"""Index operations."""

import contextlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fasteners
import sourmash

from .models import IndexFormat, SignatureName
from .io import atomic_save

LOG = logging.getLogger(__name__)


@dataclass
class AddResult:
    """Result of adding new signatures to index."""

    ok: bool
    warnings: list[str]
    added_count: int


@dataclass
class RemoveResult:
    """Result of adding new signatures to index."""

    ok: bool
    warnings: list[str]
    removed_count: int


class SourmashIndexStore:
    """Handles sourmash index on disk

    - support batch operations and atomic saves
    """

    def __init__(
        self, index_path: Path, index_format: IndexFormat, lock_path: Path | None = None
    ):
        self.index_path: Path = index_path
        self.index_format: IndexFormat = index_format
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
    def locked(self, timeout: float | None = None):
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
            LOG.warning("Invalid index: %s", self.index_path)
        self._index = index
        return self._index

    def list_signatures(self) -> list[SignatureName]:
        """List signatures in index."""
        index = self._load_index(create_if_missing=False)
        return [
            SignatureName(name=sig.name, filename=getattr(sig, "filename", ""))
            for sig in index.signatures()
        ]

    def add_signatures(
        self, signatures: Iterable, dedupe_by_md5: bool = True
    ) -> AddResult:
        """Add one or more signatures to index."""

        warnings: list[str] = []
        sigs = list(signatures)
        if not sigs:
            warnings.append("No signatures to add")
            return AddResult(ok=False, warnings=warnings, added_count=0)

        with self.locked():
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
                index.add_node(leaf)
                added += 1
                if dedupe_by_md5:
                    existing_md5.add(md5)

            atomic_save(index, write_to_path=lambda path: index.save(str(path)), inherit_perms_from=self.index_path if self.index_path.exists() else None)
        return AddResult(ok=True, warnings=warnings, added_count=added)

    def remove_signatures_by_names(self, names_to_remove: set[str]) -> RemoveResult:
        """
        Remove by signature.name by reconstructing a new SBT (SBT does not support in-place deletion).
        Returns count of removed signatures.
        """
        with self.locked():
            old_index = self._load_index(create_if_missing=False)
            kept, removed = [], 0
            for sig in old_index.signatures():
                if sig.name in names_to_remove:
                    removed += 1
                else:
                    kept.append(sig)

            new_index = sourmash.sbtmh.create_sbt_index()
            for s in kept:
                new_index.add_node(sourmash.sbtmh.SigLeaf(s.md5sum(), s))

            self._index = new_index  # replace in-memory cache
            atomic_save(self._index, write_to_path=lambda path: self._index.save(str(path)), inherit_perms_from=self.index_path if self.index_path.exists() else None)
            not_removed = set(names_to_remove) - set(removed)
            if len(not_removed) > 0:
                warn = f"could not remove {', '.join(not_removed)}"
                return RemoveResult(ok=False, warnings=[warn], removed_count=len(removed))
