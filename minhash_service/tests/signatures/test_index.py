"""Test signature index operations."""
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from minhash_service.signatures.index import (
    RocksDBIndexStore,
    SBTIndexStore,
    create_index_store,
    get_index_path,
)
from minhash_service.signatures.io import read_signatures
from minhash_service.signatures.models import IndexFormat


@pytest.fixture()
def tmp_rocksdb_index(tmp_path: Path, data_dir: Path) -> Path:
    """Create temporary index directory."""
    org = data_dir / "rocksdb31.all"
    return shutil.copytree(org, tmp_path, dirs_exist_ok=True)


@pytest.fixture()
def tmp_dupl_signature(data_dir: Path) -> Path:
    """Create temporary index directory."""
    return data_dir / "DRR237260.dupl.sig"


@pytest.fixture()
def tmp_index_dir(tmp_path: Path) -> Path:
    """Create temporary index directory."""
    idx_dir = tmp_path / "indexes"
    idx_dir.mkdir()
    return idx_dir


@pytest.fixture()
def mock_signature():
    """Create a mock signature."""
    sig = Mock()
    sig.name = "test_sample"
    sig.filename = "test.fasta"
    sig.md5sum.return_value = "abc123def456abc123def456abc12345"
    return sig


@pytest.fixture()
def mock_signature_kmer21():
    """Create a mock signature for kmer=21."""
    sig = Mock()
    sig.name = "test_sample_k21"
    sig.filename = "test_k21.fasta"
    sig.md5sum.return_value = "111111111111111111111111111111111"
    sig.ksize = 21
    return sig


@pytest.fixture()
def mock_signature_kmer51():
    """Create a mock signature for kmer=51."""
    sig = Mock()
    sig.name = "test_sample_k51"
    sig.filename = "test_k51.fasta"
    sig.md5sum.return_value = "222222222222222222222222222222222"
    sig.ksize = 51
    return sig


class TestGetIndexPath:
    """Test index path generation."""

    def test_get_index_path_creates_index_dir(self, tmp_path: Path):
        """Index directory is created if it doesn't exist."""
        sig_dir = tmp_path / "signatures"
        sig_dir.mkdir()

        path = get_index_path(sig_dir, IndexFormat.SBT)

        assert path.parent.exists()
        assert path.parent.name == "indexes"

    def test_get_index_path_sbt_format(self, tmp_path: Path):
        """SBT format uses correct naming."""
        sig_dir = tmp_path / "signatures"
        sig_dir.mkdir()

        path = get_index_path(sig_dir, IndexFormat.SBT)

        assert "genomes_sbt_index" in str(path)

    def test_get_index_path_rocksdb_format(self, tmp_path: Path):
        """RocksDB format uses correct naming."""
        sig_dir = tmp_path / "signatures"
        sig_dir.mkdir()

        path = get_index_path(sig_dir, IndexFormat.ROCKSDB)

        assert "genomes_rocksdb_index" in str(path)

    def test_get_index_path_same_dir(self, tmp_path: Path):
        """Multiple calls return same path."""
        sig_dir = tmp_path / "signatures"
        sig_dir.mkdir()

        path1 = get_index_path(sig_dir, IndexFormat.SBT)
        path2 = get_index_path(sig_dir, IndexFormat.SBT)

        assert path1 == path2


class TestCreateIndexStore:
    """Test index store factory."""

    def test_create_index_store_sbt(self, tmp_index_dir: Path):
        """Create SBT index store."""
        index_path = tmp_index_dir / "test_sbt"

        store = create_index_store(index_path, IndexFormat.SBT)

        assert isinstance(store, SBTIndexStore)

    def test_create_index_store_rocksdb(self, tmp_index_dir: Path):
        """Create RocksDB index store."""
        index_path = tmp_index_dir / "test_rocksdb"

        store = create_index_store(index_path, IndexFormat.ROCKSDB)

        assert isinstance(store, RocksDBIndexStore)

    def test_create_index_store_with_lock_path(self, tmp_index_dir: Path):
        """Create index store with custom lock path."""
        index_path = tmp_index_dir / "test"
        lock_path = tmp_index_dir / "custom.lock"

        store = create_index_store(index_path, IndexFormat.SBT, lock_path)

        assert store.lock_path == lock_path

    def test_create_index_store_invalid_format(self, tmp_index_dir: Path):
        """Invalid format raises error."""
        index_path = tmp_index_dir / "test"

        with pytest.raises(NotImplementedError):
            create_index_store(index_path, "invalid_format")


class TestSBTIndexStore:
    """Test SBT index store."""

    def test_sbt_load_creates_if_missing(self, tmp_index_dir: Path):
        """Loading creates index if file is missing."""
        index_path = tmp_index_dir / "test_sbt"

        with patch("sourmash.create_sbt_index") as mock_create:
            mock_create.return_value = Mock()
            store = SBTIndexStore(index_path)
            index = store._load_index(create_if_missing=True)

            mock_create.assert_called_once()

    def test_sbt_load_raises_if_missing_and_not_create(self, tmp_index_dir: Path):
        """Loading raises if file missing and create_if_missing=False."""
        index_path = tmp_index_dir / "nonexistent"

        with patch("sourmash.load_file_as_index", side_effect=FileNotFoundError):
            store = SBTIndexStore(index_path)
            with pytest.raises(FileNotFoundError):
                store._load_index(create_if_missing=False)

    def test_sbt_add_signatures_single(self, tmp_index_dir: Path, mock_signature):
        """Add a single signature to SBT index."""
        index_path = tmp_index_dir / "test"

        with patch("sourmash.create_sbt_index") as mock_create, patch(
            "sourmash.sbtmh.SigLeaf"
        ) as _:
            mock_index = Mock()
            mock_index.signatures.return_value = []
            mock_index.save = lambda x: x
            mock_create.return_value = mock_index

            store = SBTIndexStore(index_path)

            with patch.object(store, "_atomic_save") as mock_atomic_save:
                result = store.add_signatures([mock_signature])

            assert result.ok is True
            assert result.added_count == 1
            mock_index.add_node.assert_called_once()
            mock_atomic_save.assert_called_once()

    def test_sbt_add_signatures_multiple(
        self, tmp_index_dir: Path, mock_signature_kmer21, mock_signature_kmer51
    ):
        """Add multiple signatures to SBT index."""
        index_path = tmp_index_dir / "test"

        with patch("sourmash.create_sbt_index") as mock_create, patch(
            "sourmash.sbtmh.SigLeaf"
        ):
            mock_index = Mock()
            mock_index.signatures.return_value = []
            mock_index.save = lambda x: x
            mock_create.return_value = mock_index

            store = SBTIndexStore(index_path)

            with patch.object(store, "_atomic_save") as mock_atomic_save:
                result = store.add_signatures(
                    [mock_signature_kmer21, mock_signature_kmer51]
                )

            assert result.ok is True
            assert result.added_count == 2
            mock_atomic_save.assert_called_once()
            assert mock_index.add_node.call_count == 2

    def test_sbt_add_empty_list(self, tmp_index_dir: Path):
        """Adding empty list returns empty result."""
        index_path = tmp_index_dir / "test"

        store = SBTIndexStore(index_path)
        result = store.add_signatures([])

        assert result.ok is False
        assert result.added_count == 0

    def test_sbt_remove_signatures(self, tmp_index_dir: Path, mock_signature):
        """Remove signatures from SBT index."""
        index_path = tmp_index_dir / "test"

        with patch("sourmash.create_sbt_index") as mock_create, patch(
            "sourmash.sbtmh.SigLeaf"
        ):
            mock_index = Mock()
            mock_index.signatures.return_value = [mock_signature]
            mock_create.return_value = mock_index

            store = SBTIndexStore(index_path)
            store.index  # assert index is created
            with patch.object(store, "_atomic_save") as mock_atomic_save:
                result = store.remove_signatures({mock_signature.md5sum()})

            assert result.removed_count == 1
            mock_atomic_save.assert_called_once()

    def test_sbt_remove_nonexistent_signature(self, tmp_index_dir: Path):
        """Removing non-existent signature fails gracefully."""
        index_path = tmp_index_dir / "test"

        with patch("sourmash.create_sbt_index") as mock_create:
            mock_index = Mock()
            mock_index.signatures.return_value = []
            mock_create.return_value = mock_index

            store = SBTIndexStore(index_path)
            store.index  # assert index is created
            with patch.object(store, "_atomic_save") as mock_atomic_save:
                result = store.remove_signatures({"nonexistent_md5"})

            assert result.ok is False
            assert result.removed_count == 0
            mock_atomic_save.assert_called_once()

    def test_sbt_list_signatures(self, tmp_index_dir: Path, mock_signature):
        """List signatures from index."""
        index_path = tmp_index_dir / "test"

        with patch("sourmash.create_sbt_index") as mock_create:
            mock_index = Mock()
            mock_index.signatures.return_value = [mock_signature]
            mock_create.return_value = mock_index

            store = SBTIndexStore(index_path)
            store.index  # assert index is created
            sigs = store.list_signatures()

            assert len(sigs) == 1
            assert sigs[0].name == "test_sample"


class TestRocksDBIndexStore:
    """Test RocksDB index store."""

    def test_rocksdb_load_creates_if_missing(self, tmp_index_dir: Path):
        """Loading creates index if missing."""
        index_path = tmp_index_dir / "test_rocksdb"

        with patch("sourmash.index.revindex.DiskRevIndex") as mock_class:
            mock_index = Mock()
            mock_class.return_value = mock_index
            mock_class.create_from_sigs.return_value = mock_index

            store = RocksDBIndexStore(index_path)
            result = store._load_index(create_if_missing=True)

            assert result is not None

    def test_rocksdb_load_raises_if_missing_and_not_create(self, tmp_index_dir: Path):
        """Loading raises if file missing and create_if_missing=False."""
        index_path = tmp_index_dir / "nonexistent"

        with patch(
            "sourmash.index.revindex.DiskRevIndex", side_effect=FileNotFoundError
        ):
            store = RocksDBIndexStore(index_path)
            with pytest.raises(FileNotFoundError):
                store._load_index(create_if_missing=False)

    def test_rocksdb_list_signatures(self, tmp_index_dir: Path, mock_signature):
        """List signatures from RocksDB index."""
        index_path = tmp_index_dir / "test"

        with patch("sourmash.index.revindex.DiskRevIndex") as mock_class:
            mock_index = Mock()
            mock_index.signatures.return_value = [mock_signature]
            mock_class.return_value = mock_index

            store = RocksDBIndexStore(index_path)
            store.index  # assert index is created
            sigs = store.list_signatures()

            assert len(sigs) == 1

    def test_rocksdb_add_signature(self, tmp_rocksdb_index: Path, tmp_dupl_signature: Path):
        """Use the actual database to test adding a signature."""

        store = RocksDBIndexStore(tmp_rocksdb_index)

        start_n_sigs = len(store.list_signatures())

        # add a signature to the db
        sigs = [sig for sig in read_signatures(tmp_dupl_signature) if sig.minhash.ksize == 31]
        status = store.add_signatures(sigs)

        assert status.ok

        assert len(store.list_signatures()) == start_n_sigs + 1

    def test_rocksdb_remove_signature(self, tmp_rocksdb_index: Path):
        """Use the actual database to test removing a signature."""

        store = RocksDBIndexStore(tmp_rocksdb_index)

        start_sigs = store.list_signatures()
        start_n_sigs = len(start_sigs)
        assert start_n_sigs > 0, "Index must have at least one signature to test removal"

        # remove the first signature
        sig_to_remove = start_sigs[0]
        md5_to_remove = None
        for sig in store.index.signatures():
            if sig.name == sig_to_remove.name:
                md5_to_remove = sig.md5sum()
                break

        assert md5_to_remove is not None
        status = store.remove_signatures({md5_to_remove})

        assert status.ok
        assert len(store.list_signatures()) == start_n_sigs - 1 


class TestLockManagement:
    """Test lock management across index stores."""

    def test_acquire_lock_success(self, tmp_index_dir: Path):
        """Successfully acquire lock."""
        index_path = tmp_index_dir / "test"

        store = SBTIndexStore(index_path)
        with store.aquire_lock():
            # Lock should be held
            assert store.lock_path.parent.exists()

    def test_acquire_lock_multiple_stores(self, tmp_index_dir: Path):
        """Multiple stores can share same lock."""
        index_path = tmp_index_dir / "test"
        lock_path = tmp_index_dir / "shared.lock"

        store1 = SBTIndexStore(index_path, lock_path)
        store2 = SBTIndexStore(index_path, lock_path)

        assert store1.lock_path == store2.lock_path

    def test_lock_path_default(self, tmp_index_dir: Path):
        """Default lock path is derived from index path."""
        index_path = tmp_index_dir / "test"

        store = SBTIndexStore(index_path)

        assert ".lock" in str(store.lock_path)


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_add_signatures_handles_sourmash_error(
        self, tmp_index_dir: Path, mock_signature
    ):
        """Handle sourmash errors gracefully during add."""
        index_path = tmp_index_dir / "test"

        with patch(
            "sourmash.create_sbt_index", side_effect=Exception("Sourmash error")
        ):
            store = SBTIndexStore(index_path)
            with pytest.raises(Exception):
                store.add_signatures([mock_signature])

    def test_remove_signatures_handles_sourmash_error(self, tmp_index_dir: Path):
        """Handle sourmash errors gracefully during remove."""
        index_path = tmp_index_dir / "test"

        with patch(
            "sourmash.create_sbt_index", side_effect=Exception("Sourmash error")
        ):
            store = SBTIndexStore(index_path)
            with pytest.raises(Exception):
                store.remove_signatures({"checksum"})

    def test_rocksdb_rebuild_on_error(self, tmp_index_dir: Path, mock_signature):
        """RocksDB rebuild handles errors."""
        index_path = tmp_index_dir / "test"

        with patch("sourmash.index.revindex.DiskRevIndex") as mock_class:
            mock_class.create_from_sigs.side_effect = Exception("Rebuild failed")

            store = RocksDBIndexStore(index_path)
            result = store.add_signatures([mock_signature])

            assert result.ok is False
            assert len(result.warnings) > 0
