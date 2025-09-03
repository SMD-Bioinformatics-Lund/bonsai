"""Sourmash index operations."""

import contextlib
import logging
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

import fasteners
import sourmash
from pydantic import BaseModel
from sourmash.exceptions import Panic
from sourmash.index.revindex import DiskRevIndex

from .models import IndexFormat, SignatureName, SourmashSignatures

LOG = logging.getLogger(__name__)


def get_index_path(signature_dir: Path, fmt: IndexFormat) -> Path:
    idx_dir = signature_dir / "indexes"
    idx_dir.mkdir(exist_ok=True)
    return idx_dir / f"genomes_{fmt.value.lower()}_index"


def create_index_store(
    index_path: Path, index_format: IndexFormat, lock_path: Path | None = None
) -> "BaseIndexStore":
    """Create an index store based on the specified format."""
    LOG.debug("Reading index from: %s; format: %s", index_path, index_format)
    if index_format == IndexFormat.SBT:
        idx = SBTIndexStore(index_path, lock_path)
    elif index_format == IndexFormat.ROCKSDB:
        idx = RocksDBIndexStore(index_path, lock_path)
    else:
        raise NotImplementedError(f"Unknown index format: {index_format}")
    return idx


class AddResult(BaseModel):
    """Result of adding new signatures to index."""

    ok: bool
    warnings: list[str]
    added_count: int
    added_md5s: list[str]


class RemoveResult(BaseModel):
    """Result of adding new signatures to index."""

    ok: bool
    warnings: list[str]
    removed_count: int
    removed: list[str] = []


class BaseIndexStore(ABC):
    """Base class for index stores."""

    def __init__(self, index_path: Path, lock_path: Path | None = None):
        """Initialize the index store with the given path and optional lock path."""

        # Ensure index_path is a Path object
        if isinstance(index_path, str):
            index_path = Path(index_path)

        self.index_path: Path = index_path
        # Put the lock near the index by default to scope correctly on multi-host systems
        self.lock_path = (
            lock_path
            if lock_path
            else self.index_path.with_suffix(f"{self.index_path.suffix}.lock")
        )
        self._lock = fasteners.InterProcessLock(str(self.lock_path))
        self._index = None  # lazy loaded
        LOG.debug("Index path: %s; lock path: %s", self.index_path, self.lock_path)

    @contextlib.contextmanager
    def aquire_lock(self, timeout: float | None = None):
        """
        Acquire an interprocess lock for the duration of the block.
        Use this to compose multiple ops transactionally.
        """
        LOG.debug("Acquiring lock: %s", self.lock_path)
        acquired = self._lock.acquire(blocking=True, timeout=timeout)
        if not acquired:
            raise TimeoutError(f"Could not acquire lock: {self.lock_path}")
        try:
            yield
        finally:
            self._lock.release()
            LOG.debug("Released lock: %s", self.lock_path)

    @abstractmethod
    def list_signatures(self) -> list[SignatureName]:
        """List signatures in index."""

    @abstractmethod
    def add_signatures(
        self,
        signatures: Iterable[sourmash.SourmashSignature],
        dedupe_by_md5: bool = True,
    ) -> AddResult:
        """Add one or more signatures to index."""

    @abstractmethod
    def remove_signatures(self, names_to_remove: set[str]) -> RemoveResult:
        """Remove signatures by name."""


class SBTIndexStore(BaseIndexStore):
    """Handles sourmash SBT index on disk

    - support batch operations and atomic saves
    """

    def _load_index(self, create_if_missing: bool = True):
        """Load index to memory."""
        if self._index is not None:
            return self._index

        try:
            index = sourmash.load_file_as_index(str(self.index_path))
            LOG.debug(
                "Loaded index '%s' (type: %s)", self.index_path, type(index).__name__
            )
        except (FileNotFoundError, ValueError):
            if not create_if_missing:
                raise
            LOG.warning("Invalid index: %s, creating new index", self.index_path)
            index = sourmash.create_sbt_index()
        self._index = index
        return self._index

    def _atomic_save(self):
        """Index specific atomic save."""

        parent = self.index_path.parent  # keep on same file system
        with tempfile.TemporaryDirectory(
            dir=parent, prefix=self.index_path.name
        ) as tmp_dir:
            tmp_dir = Path(tmp_dir)
            tmp_idx_path = self._index.save(str(tmp_dir / "index"))
            tmp_idx_path = Path(tmp_idx_path)  # str -> Path

            tmp_idx_path.replace(self.index_path)

    def list_signatures(self) -> list[SignatureName]:
        """List signatures in index."""
        index = self._load_index(create_if_missing=False)
        return [
            SignatureName(name=sig.name, filename=getattr(sig, "filename", ""))
            for sig in index.signatures()
        ]

    def add_signatures(
        self,
        signatures: Iterable[sourmash.SourmashSignature],
        dedupe_by_md5: bool = True,
    ) -> AddResult:
        """Add one or more signatures to index."""

        warnings: list[str] = []
        sigs = list(signatures)
        if not sigs:
            warnings.append("No signatures to add")
            return AddResult(ok=False, warnings=warnings, added_count=0)

        added_md5s: list[str] = []
        with self.aquire_lock():
            index = self._load_index(create_if_missing=True)

            existing_md5 = set()
            if dedupe_by_md5:
                for sig in index.signatures():
                    existing_md5.add(sig.md5sum())

            added: int = 0
            for sig in sigs:
                md5 = sig.md5sum()
                if dedupe_by_md5 and md5 in existing_md5:
                    continue
                # add signature depending on the db type
                leaf = sourmash.sbtmh.SigLeaf(md5, sig)
                self._index.add_node(leaf)
                added += 1
                added_md5s.append(md5)
                if dedupe_by_md5:
                    existing_md5.add(md5)
            self._atomic_save()
        return AddResult(
            ok=True, warnings=warnings, added_count=added, added_md5s=added_md5s
        )

    def remove_signatures(self, names_to_remove: list[str]) -> RemoveResult:
        """
        Remove by signature.name by reconstructing a new SBT.
        SBT does not support in-place deletion.
        Returns count of removed signatures.
        """
        with self.aquire_lock():
            old_index = self._load_index(create_if_missing=False)
            kept: SourmashSignatures = []
            removed: list[str] = []
            for sig in old_index.signatures():
                if sig.name in names_to_remove:
                    removed.append(sig.name)
                else:
                    kept.append(sig)

            new_index = sourmash.sbtmh.create_sbt_index()
            for s in kept:
                new_index.add_node(sourmash.sbtmh.SigLeaf(s.md5sum(), s))

            self._index = new_index  # replace in-memory cache
            self._atomic_save()
            not_removed = set(names_to_remove) - set(removed)
            if len(not_removed) > 0:
                warn = f"could not remove {', '.join(not_removed)}"
                return RemoveResult(
                    ok=False, warnings=[warn], removed_count=len(removed)
                )
        return RemoveResult(
            ok=False, warnings=[], removed_count=len(removed), removed=removed
        )


class RocksDBIndexStore(BaseIndexStore):
    """Handles RocksDB index on disk."""

    def _load_index(self, create_if_missing: bool = True):
        try:
            index = DiskRevIndex(str(self.index_path))
            LOG.debug(
                "Loaded index '%s' (type: %s)", self.index_path, type(index).__name__
            )
        except (FileNotFoundError, ValueError):
            if not create_if_missing:
                raise
            LOG.warning("Invalid index: %s, creating new index", self.index_path)
            index = DiskRevIndex.create_from_sigs([], str(self.index_path))
        except Panic as err:
            LOG.error("Sourmash failed to load index: %s", err)
        return index

    def list_signatures(self) -> list[SignatureName]:
        """List signatures in index."""
        index = self._load_index(create_if_missing=True)
        return [
            SignatureName(name=sig.name, filename=getattr(sig, "filename", ""))
            for sig in index.signatures()
        ]

    def add_signatures(
        self,
        signatures: Iterable[sourmash.SourmashSignature],
        dedupe_by_md5: bool = True,
    ):
        """Add one or more signatures to index."""
        warnings: list[str] = []
        sigs = list(signatures)
        if not sigs:
            warnings.append("No signatures to add")
            return AddResult(ok=False, warnings=warnings, added_count=0)
        raise NotImplementedError(
            "RocksDBIndexStore does not support adding signatures directly."
        )

    def remove_signatures(self, names_to_remove: set[str]) -> RemoveResult:
        """Remove signatures by name."""
        raise NotImplementedError(
            "RocksDBIndexStore does not support adding signatures directly."
        )
