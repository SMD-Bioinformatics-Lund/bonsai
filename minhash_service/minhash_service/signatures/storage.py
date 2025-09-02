"""Manage the storage of signatures in the service."""

import datetime as dt
import json
import logging
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

LOG = logging.getLogger(__name__)


@dataclass
class SignatureStorage:
    """Manage storage of signatures on disk."""

    base_dir: Path
    trash_dir: Path

    def file_sha256_hex(self, path: Path, chunk_size: int = 8192) -> str:
        """Calculate sha256 checksum of a file."""
        checksum = sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                checksum.update(chunk)
        return checksum.hexdigest()

    def cannonical_path(self, checksum: str) -> Path:
        """
        Get a directory path from the checksum.

        This creates a directory structure like:
        /<base_dir>/<c0>/<c1>/<checksum>.sig
        """
        return (
            self.base_dir
            / checksum[:2].lower()
            / checksum[2:4].lower()
            / f"{checksum}.sig"
        )

    def ensure_file(self, tmp_path: Path, checksum: str) -> Path:
        """Move a file to its sharded directory based on checksum."""
        dest_path = self.cannonical_path(checksum)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # optional file deduplication
        if dest_path.exists():
            LOG.warning(
                "File with checksum %s already exists at %s", checksum, dest_path
            )
            tmp_path.unlink()
            return dest_path

        # atomic move on the file system
        tmp_path.replace(dest_path)

        return dest_path

    def _trash_path(
        self, checksum: str, when: dt.datetime, filename: str | None = None
    ) -> Path:
        """Get the path in the trash directory."""
        if filename is None:
            filename = f"{checksum}.sig"
        return (
            self.trash_dir
            / str(when.year)
            / checksum[:2].lower()
            / checksum[2:4].lower()
            / filename
        )

    def move_to_trash(self, cannonical: Path, checksum: str) -> Path:
        """Move a file to the trash directory using its cannonical path."""
        if not cannonical.exists():
            raise FileNotFoundError(f"File {cannonical} does not exist, cant trash it.")

        when = dt.datetime.now(dt.timezone.utc)
        target = self._trash_path(checksum, when, cannonical.name)
        target.parent.mkdir(parents=True, exist_ok=True)

        # sidecar metadata for file cleanup
        meta: dict[str, str] = {
            "checksum": checksum,
            "size": str(cannonical.stat().st_size),
            "deleted_at": when.isoformat(),
        }
        target.parent.joinpath(f"{target.name}.json").write_text(
            json.dumps(meta, indent=2)
        )

        cannonical.replace(target)
        LOG.info("Moved %s to trash at %s", cannonical, target)
        return target

    def check_file_integrity(self, path: Path, expected_checksum: str) -> bool:
        """Check if the file at the given path matches the expected checksum."""
        if not path.exists():
            LOG.error("File %s does not exist for integrity check.", path)
            return False
        actual_checksum = self.file_sha256_hex(path)
        if actual_checksum != expected_checksum:
            LOG.error(
                "Checksum mismatch for %s: expected %s, got %s",
                path,
                expected_checksum,
                actual_checksum,
            )
            return False
        return True

    def purge_path(self, path: Path) -> None:
        """Permanently delete a file from the trash directory."""
        path.unlink(missing_ok=True)
        sidecar = path.with_suffix(path.suffix + ".json")
        sidecar.unlink(missing_ok=True)

    def purge_older_than(self, cutoff: dt.datetime) -> int:
        """Permanently delete files older than a timestamp from the trash directory."""
        removed_count: int = 0
        if not self.trash_dir.exists():
            raise FileNotFoundError(f"Trash directory {self.trash_dir} does not exist.")

        for path in self.trash_dir.rglob("*.sig"):
            try:
                sidecar = path.with_suffix(path.suffix + ".json")
                meta = json.loads(sidecar.read_text())
                deleted_at = dt.datetime.fromisoformat(meta["deleted_at"])
                if deleted_at < cutoff:
                    self.purge_path(path)
                    removed_count += 1

                    LOG.info("Purged %s and its metadata", path)
            except Exception as err:
                LOG.error("Error processing %s: %s", path, err)
                continue
        return removed_count
