"""Test signature storage operations."""

import datetime as dt
import json
from pathlib import Path

import pytest

from minhash_service.signatures.storage import SignatureStorage


@pytest.fixture()
def storage(tmp_path: Path) -> SignatureStorage:
    """Create storage instance with temporary directories."""
    base_dir = tmp_path / "signatures"
    trash_dir = tmp_path / "trash"
    base_dir.mkdir()
    trash_dir.mkdir()
    return SignatureStorage(base_dir=base_dir, trash_dir=trash_dir)


@pytest.fixture()
def test_file(tmp_path: Path) -> Path:
    """Create a test file."""
    test_file = tmp_path / "test.sig"
    test_file.write_text('{"test": "data"}', encoding="utf-8")
    return test_file


class TestFileChecksum:
    """Test file checksum calculation."""

    def test_file_sha256_hex_calculates_checksum(self, test_file: Path):
        """Calculate SHA256 checksum of a file."""
        storage = SignatureStorage(base_dir=Path("/tmp"), trash_dir=Path("/tmp"))
        checksum = storage.file_sha256_hex(test_file)

        assert len(checksum) == 64  # SHA256 hex is 64 chars
        assert all(c in "0123456789abcdef" for c in checksum)

    def test_file_sha256_hex_consistent(self, test_file: Path):
        """Checksum is consistent across multiple calls."""
        storage = SignatureStorage(base_dir=Path("/tmp"), trash_dir=Path("/tmp"))
        checksum1 = storage.file_sha256_hex(test_file)
        checksum2 = storage.file_sha256_hex(test_file)

        assert checksum1 == checksum2

    def test_file_sha256_hex_differs_for_different_files(self, tmp_path: Path):
        """Different files produce different checksums."""
        storage = SignatureStorage(base_dir=Path("/tmp"), trash_dir=Path("/tmp"))

        file1 = tmp_path / "file1.txt"
        file1.write_text("content1")
        checksum1 = storage.file_sha256_hex(file1)

        file2 = tmp_path / "file2.txt"
        file2.write_text("content2")
        checksum2 = storage.file_sha256_hex(file2)

        assert checksum1 != checksum2

    def test_file_sha256_hex_large_file(self, tmp_path: Path):
        """Handle large files correctly."""
        storage = SignatureStorage(base_dir=Path("/tmp"), trash_dir=Path("/tmp"))

        large_file = tmp_path / "large.bin"
        # Create a 10MB file
        with large_file.open("wb") as f:
            f.write(b"x" * (10 * 1024 * 1024))

        checksum = storage.file_sha256_hex(large_file)
        assert len(checksum) == 64


class TestCannonicalPath:
    """Test sharded directory path generation."""

    def test_cannonical_path_structure(self, storage: SignatureStorage):
        """Cannonical path uses first 4 hex chars for sharding."""
        checksum = "abcd1234567890fedcba9876543210"
        path = storage.cannonical_path(checksum)

        # Should be: base_dir/ab/cd/abcd...sig
        assert path.name == f"{checksum}.sig"
        assert path.parent.name == "cd"
        assert path.parent.parent.name == "ab"
        assert path.parent.parent.parent == storage.base_dir

    def test_cannonical_path_lowercase(self, storage: SignatureStorage):
        """Cannonical path converts to lowercase."""
        checksum = "ABCD1234567890FEDCBA9876543210"
        path = storage.cannonical_path(checksum)

        assert path.parent.name == "cd"
        assert path.parent.parent.name == "ab"

    def test_cannonical_path_different_checksums(self, storage: SignatureStorage):
        """Different checksums produce different paths."""
        path1 = storage.cannonical_path("aaaa1111111111111111111111111111")
        path2 = storage.cannonical_path("bbbb2222222222222222222222222222")

        assert path1 != path2
        assert path1.parent.parent.name == "aa"
        assert path2.parent.parent.name == "bb"


class TestEnsureFile:
    """Test file movement to sharded storage."""

    def test_ensure_file_moves_file(self, storage: SignatureStorage, test_file: Path):
        """Move file to sharded directory."""
        checksum = "abc123def456abc123def456abc12345"

        result = storage.ensure_file(test_file, checksum)

        # File should be at cannonical path
        expected = storage.cannonical_path(checksum)
        assert result == expected
        assert result.exists()
        assert not test_file.exists()

    def test_ensure_file_creates_parent_directories(
        self, storage: SignatureStorage, test_file: Path
    ):
        """Parent directories are created if needed."""
        checksum = "abc123def456abc123def456abc12345"

        result = storage.ensure_file(test_file, checksum)

        assert result.parent.exists()
        assert result.parent.parent.exists()

    def test_ensure_file_deduplication_existing_file(
        self, storage: SignatureStorage, test_file: Path
    ):
        """Duplicate file is deleted, existing file kept."""
        checksum = "abc123def456abc123def456abc12345"

        # First call
        result1 = storage.ensure_file(test_file, checksum)
        assert result1.exists()

        # Create another file
        test_file2 = test_file.parent / "test2.sig"
        test_file2.write_text('{"test": "data"}', encoding="utf-8")

        # Second call with same checksum
        result2 = storage.ensure_file(test_file2, checksum)

        # Should return same path and original file should be kept
        assert result2 == result1
        assert result1.exists()
        assert not test_file2.exists()

    def test_ensure_file_preserves_content(
        self, storage: SignatureStorage, tmp_path: Path
    ):
        """File content is preserved after moving."""
        test_file = tmp_path / "original.txt"
        content = "important data here"
        test_file.write_text(content)
        checksum = "abc123def456abc123def456abc12345"

        result = storage.ensure_file(test_file, checksum)

        assert result.read_text() == content


class TestTrashOperations:
    """Test file trashing and cleanup."""

    def test_move_to_trash_creates_trash_file(
        self, storage: SignatureStorage, test_file: Path
    ):
        """Move file to trash."""
        checksum = "abc123def456abc123def456abc12345"
        # First ensure it's at cannonical path
        cannonical = storage.ensure_file(test_file, checksum)

        # Move to trash
        trash_path = storage.move_to_trash(cannonical, checksum)

        assert trash_path.exists()
        assert not cannonical.exists()

    def test_move_to_trash_creates_metadata(
        self, storage: SignatureStorage, test_file: Path
    ):
        """Metadata sidecar file is created with deletion info."""
        checksum = "abc123def456abc123def456abc12345"
        cannonical = storage.ensure_file(test_file, checksum)

        trash_path = storage.move_to_trash(cannonical, checksum)

        # Check metadata file exists
        metadata_path = trash_path.with_suffix(trash_path.suffix + ".json")
        assert metadata_path.exists()

        # Verify metadata content
        metadata = json.loads(metadata_path.read_text())
        assert metadata["checksum"] == checksum
        assert "deleted_at" in metadata
        assert "size" in metadata

    def test_move_to_trash_uses_date_in_path(
        self, storage: SignatureStorage, test_file: Path
    ):
        """Trash path includes year for organization."""
        checksum = "abc123def456abc123def456abc12345"
        cannonical = storage.ensure_file(test_file, checksum)

        trash_path = storage.move_to_trash(cannonical, checksum)

        # Path should include year
        current_year = str(dt.datetime.now(dt.timezone.utc).year)
        assert current_year in trash_path.parts

    def test_move_to_trash_nonexistent_file_raises(
        self, storage: SignatureStorage
    ):
        """Moving non-existent file raises error."""
        nonexistent = storage.base_dir / "nonexistent.sig"

        with pytest.raises(FileNotFoundError):
            storage.move_to_trash(nonexistent, "checksum")

    def test_purge_path_deletes_file(
        self, storage: SignatureStorage, test_file: Path
    ):
        """Purge removes file from trash."""
        checksum = "abc123def456abc123def456abc12345"
        cannonical = storage.ensure_file(test_file, checksum)
        trash_path = storage.move_to_trash(cannonical, checksum)

        storage.purge_path(trash_path)

        assert not trash_path.exists()

    def test_purge_path_deletes_metadata(
        self, storage: SignatureStorage, test_file: Path
    ):
        """Purge removes metadata sidecar."""
        checksum = "abc123def456abc123def456abc12345"
        cannonical = storage.ensure_file(test_file, checksum)
        trash_path = storage.move_to_trash(cannonical, checksum)
        metadata_path = trash_path.with_suffix(trash_path.suffix + ".json")

        storage.purge_path(trash_path)

        assert not metadata_path.exists()

    def test_purge_path_missing_ok(self, storage: SignatureStorage):
        """Purging non-existent file doesn't raise."""
        nonexistent = storage.trash_dir / "nonexistent.sig"
        # Should not raise
        storage.purge_path(nonexistent)


class TestFileIntegrity:
    """Test file integrity checking."""

    def test_check_file_integrity_valid(
        self, storage: SignatureStorage, test_file: Path
    ):
        """File integrity check passes for valid file."""
        checksum = storage.file_sha256_hex(test_file)

        result = storage.check_file_integrity(test_file, checksum)

        assert result is True

    def test_check_file_integrity_mismatch(
        self, storage: SignatureStorage, test_file: Path
    ):
        """File integrity check fails for mismatched checksum."""
        wrong_checksum = "0000000000000000000000000000000000000000000000000000000000000000"

        result = storage.check_file_integrity(test_file, wrong_checksum)

        assert result is False

    def test_check_file_integrity_missing_file(self, storage: SignatureStorage):
        """File integrity check fails for missing file."""
        nonexistent = storage.base_dir / "nonexistent.sig"

        result = storage.check_file_integrity(nonexistent, "anyChecksum")

        assert result is False


class TestPurgeOlderThan:
    """Test cleanup of old files."""

    def test_purge_older_than_removes_old_files(
        self, storage: SignatureStorage, test_file: Path
    ):
        """Purge removes files older than cutoff."""
        checksum = "abc123def456abc123def456abc12345"
        cannonical = storage.ensure_file(test_file, checksum)
        trash_path = storage.move_to_trash(cannonical, checksum)

        # Manually update metadata to old date
        metadata_path = trash_path.with_suffix(trash_path.suffix + ".json")
        old_date = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
        metadata = json.loads(metadata_path.read_text())
        metadata["deleted_at"] = old_date.isoformat()
        metadata_path.write_text(json.dumps(metadata))

        # Set cutoff to 1 week ago
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
        removed = storage.purge_older_than(cutoff)

        assert removed == 1
        assert not trash_path.exists()

    def test_purge_older_than_keeps_recent_files(
        self, storage: SignatureStorage, test_file: Path
    ):
        """Purge keeps files newer than cutoff."""
        checksum = "abc123def456abc123def456abc12345"
        cannonical = storage.ensure_file(test_file, checksum)
        trash_path = storage.move_to_trash(cannonical, checksum)

        # Set cutoff to 1 week ago
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
        removed = storage.purge_older_than(cutoff)

        # Recently deleted file should not be removed
        assert removed == 0
        assert trash_path.exists()

    def test_purge_older_than_multiple_files(
        self, storage: SignatureStorage, tmp_path: Path
    ):
        """Purge handles multiple files correctly."""
        # Create and trash 3 files
        for i in range(3):
            test_file = tmp_path / f"test{i}.sig"
            test_file.write_text(f"data{i}")
            checksum = f"abc123def456abc123def456abc1234{i}"
            cannonical = storage.ensure_file(test_file, checksum)
            trash_path = storage.move_to_trash(cannonical, checksum)

            # Update metadata - alternate old and new
            if i < 2:  # First two are old
                metadata_path = trash_path.with_suffix(trash_path.suffix + ".json")
                old_date = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
                metadata = json.loads(metadata_path.read_text())
                metadata["deleted_at"] = old_date.isoformat()
                metadata_path.write_text(json.dumps(metadata))

        # Set cutoff to 1 week ago
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
        removed = storage.purge_older_than(cutoff)

        # Should remove 2 old files, keep 1 recent
        assert removed == 2

    def test_purge_older_than_missing_trash_raises(self, tmp_path: Path):
        """Purge raises if trash directory doesn't exist."""
        storage = SignatureStorage(
            base_dir=tmp_path / "sigs", trash_dir=tmp_path / "nonexistent_trash"
        )

        with pytest.raises(FileNotFoundError):
            storage.purge_older_than(dt.datetime.now(dt.timezone.utc))

    def test_purge_older_than_handles_invalid_metadata(
        self, storage: SignatureStorage, test_file: Path
    ):
        """Purge handles corrupted metadata gracefully."""
        checksum = "abc123def456abc123def456abc12345"
        cannonical = storage.ensure_file(test_file, checksum)
        trash_path = storage.move_to_trash(cannonical, checksum)

        # Corrupt metadata file
        metadata_path = trash_path.with_suffix(trash_path.suffix + ".json")
        metadata_path.write_text("invalid json {{{")

        # Should not raise, just skip this file
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
        removed = storage.purge_older_than(cutoff)

        # File should still exist because parsing failed
        assert removed == 0
        assert trash_path.exists()