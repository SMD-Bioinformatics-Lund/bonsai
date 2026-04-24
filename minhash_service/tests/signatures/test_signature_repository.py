"""Test SignatureRepository with multi-kmer support."""

import pytest
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

from minhash_service.signatures.models import SignatureRecord
from minhash_service.signatures.repository import SignatureRepository


@pytest.fixture
def mock_collection(mocker):
    """Mock MongoDB collection."""
    return mocker.MagicMock(spec=Collection)


@pytest.fixture
def repo(mock_collection):
    """Create repository instance with mock collection."""
    return SignatureRepository(mock_collection)


class TestSchemaManagement:
    """Test index creation and schema setup."""

    def test_ensure_indexes_creates_composite_index(self, repo):
        """Verify composite (sample_id, kmer_size) index is created."""
        repo.ensure_indexes()

        # Verify create_index called for composite index
        calls = repo._col.create_index.call_args_list
        assert len(calls) >= 1

        # Check composite index
        composite_index = calls[0][0][0]
        assert ("sample_id", 1) in composite_index
        assert ("kmer_size", 1) in composite_index

    def test_ensure_indexes_unique_constraint(self, repo):
        """Verify unique constraint on composite index."""
        repo.ensure_indexes()

        calls = repo._col.create_index.call_args_list
        composite_call = calls[0]
        kwargs = composite_call[1]
        assert kwargs.get("unique") is True

    def test_ensure_indexes_has_been_indexed_index(self, repo):
        """Verify index on has_been_indexed flag."""
        repo.ensure_indexes()

        calls = repo._col.create_index.call_args_list
        assert len(calls) >= 2

        # Check has_been_indexed index
        indexed_index = calls[1][0][0]
        assert ("has_been_indexed", 1) in indexed_index


class TestAddSignature:
    """Test signature creation."""

    def test_add_single_signature(self, repo):
        """Add a single signature."""
        repo._col.insert_one.return_value.inserted_id = "id_123"

        sig = SignatureRecord(
            sample_id="sample_1",
            kmer_size=21,
            signature_path="path/to/sig",
            signature_checksum="check_abc",
            file_checksum="file_abc",
        )

        result = repo.add_signature(sig)

        assert result == "id_123"
        repo._col.insert_one.assert_called_once()

    def test_add_multiple_kmers_same_sample(self, repo):
        """Add multiple kmer variants for same sample."""
        repo._col.insert_one.return_value.inserted_id = "id_123"

        sig_21 = SignatureRecord(
            sample_id="sample_1",
            kmer_size=21,
            signature_path="path/to/sig_21",
            signature_checksum="check_abc",
            file_checksum="file_abc",
        )
        sig_31 = SignatureRecord(
            sample_id="sample_1",
            kmer_size=31,
            signature_path="path/to/sig_31",
            signature_checksum="check_def",
            file_checksum="file_def",
        )

        result_21 = repo.add_signature(sig_21)
        result_31 = repo.add_signature(sig_31)

        assert result_21 == "id_123"
        assert result_31 == "id_123"
        assert repo._col.insert_one.call_count == 2

    def test_add_duplicate_signature_same_kmer(self, repo):
        """Adding duplicate (sample_id + kmer_size) returns None."""
        repo._col.insert_one.side_effect = DuplicateKeyError("Duplicate key")

        sig = SignatureRecord(
            sample_id="sample_1",
            kmer_size=21,
            signature_path="path/to/sig",
            signature_checksum="check_abc",
            file_checksum="file_abc",
        )

        result = repo.add_signature(sig)

        assert result is None

    def test_add_many_signatures(self, repo):
        """Bulk insert multiple signatures."""
        repo._col.insert_many.return_value.inserted_ids = ["id_1", "id_2", "id_3"]

        sigs = [
            SignatureRecord(
                sample_id=f"sample_{i}",
                kmer_size=21 + i,
                signature_path=f"path_{i}",
                signature_checksum=f"check_{i}",
                file_checksum=f"file_{i}",
            )
            for i in range(3)
        ]

        results = repo.add_many(sigs)

        assert len(results) == 3
        repo._col.insert_many.assert_called_once()


class TestGetByQuery:
    """Test read operations with various query combinations."""

    def test_get_by_sample_id_returns_all_kmers(self, repo):
        """Query by sample_id returns all kmer variants."""
        repo._col.find.return_value.alive = True
        repo._col.find.return_value.__iter__ = lambda self: iter(
            [
                {
                    "sample_id": "sample_1",
                    "kmer_size": 21,
                    "signature_checksum": "check_abc",
                    "file_checksum": "file_abc",
                    "signature_path": "path/to/sig",
                },
                {
                    "sample_id": "sample_1",
                    "kmer_size": 31,
                    "signature_checksum": "check_def",
                    "file_checksum": "file_def",
                    "signature_path": "path/to/sig",
                },
            ]
        )

        results = repo.get_by_sample_id_or_checksum(sample_id="sample_1")

        assert len(results) == 2
        assert results[0].kmer_size == 21
        assert results[1].kmer_size == 31

        # Verify query filter
        call_args = repo._col.find.call_args
        assert call_args[0][0] == {"sample_id": "sample_1"}

    def test_get_by_sample_id_and_kmer_size(self, repo):
        """Query by sample_id + kmer_size returns specific variant."""
        repo._col.find.return_value.alive = True
        repo._col.find.return_value.__iter__ = lambda self: iter(
            [
                {
                    "sample_id": "sample_1",
                    "kmer_size": 21,
                    "signature_checksum": "check_abc",
                    "file_checksum": "file_abc",
                    "signature_path": "path/to/sig",
                },
            ]
        )

        results = repo.get_by_sample_id_or_checksum(sample_id="sample_1", kmer_size=21)

        assert len(results) == 1
        assert results[0].kmer_size == 21

        # Verify query includes kmer_size filter
        call_args = repo._col.find.call_args
        query = call_args[0][0]
        assert query["sample_id"] == "sample_1"
        assert query["kmer_size"] == 21

    def test_get_by_checksum_returns_all_kmers(self, repo):
        """Query by checksum returns all kmer variants."""
        repo._col.find.return_value.alive = True
        repo._col.find.return_value.__iter__ = lambda self: iter(
            [
                {
                    "sample_id": "sample_1",
                    "kmer_size": 21,
                    "signature_checksum": "check_abc",
                    "file_checksum": "file_abc",
                    "signature_path": "path/to/sig1",
                },
                {
                    "sample_id": "sample_2",
                    "kmer_size": 21,
                    "signature_checksum": "check_abc",
                    "file_checksum": "file_abc",
                    "signature_path": "path/to/sig2",
                },
            ]
        )

        results = repo.get_by_sample_id_or_checksum(checksum="check_abc")

        assert len(results) == 2

    def test_get_by_checksum_and_kmer_size(self, repo):
        """Query by checksum + kmer_size."""
        repo._col.find.return_value.alive = True
        repo._col.find.return_value.__iter__ = lambda self: iter(
            [
                {
                    "sample_id": "sample_1",
                    "kmer_size": 21,
                    "signature_checksum": "check_abc",
                    "file_checksum": "file_abc",
                    "signature_path": "path/to/sig1",
                },
            ]
        )

        results = repo.get_by_sample_id_or_checksum(checksum="check_abc", kmer_size=21)

        call_args = repo._col.find.call_args
        query = call_args[0][0]
        assert query["signature_checksum"] == "check_abc"
        assert query["kmer_size"] == 21

    def test_get_not_found_returns_none(self, repo):
        """Query returns None when no match."""
        repo._col.find.return_value.alive = False

        results = repo.get_by_sample_id_or_checksum(sample_id="nonexistent")

        assert results is None

    def test_get_requires_sample_id_or_checksum(self, repo):
        """Query must specify either sample_id or checksum."""
        with pytest.raises(ValueError, match="Either sample_id or checksum"):
            repo.get_by_sample_id_or_checksum()

    def test_get_rejects_both_sample_id_and_checksum(self, repo):
        """Query cannot specify both sample_id and checksum."""
        with pytest.raises(ValueError, match="Both sample_id and checksum"):
            repo.get_by_sample_id_or_checksum(
                sample_id="sample_1", checksum="check_abc"
            )


class TestIterators:
    """Test iteration methods."""

    def test_get_all_signatures(self, repo):
        """Iterate over all signatures."""
        repo._col.find.return_value.__iter__ = lambda self: iter(
            [
                {
                    "sample_id": "sample_1",
                    "kmer_size": 21,
                    "signature_checksum": "check_abc",
                    "file_checksum": "file_abc",
                    "signature_path": "path/to/sig1",
                },
                {
                    "sample_id": "sample_1",
                    "kmer_size": 31,
                    "signature_checksum": "check_abc",
                    "file_checksum": "file_abc",
                    "signature_path": "path/to/sig1",
                },
            ]
        )

        results = list(repo.get_all_signatures())

        assert len(results) == 2
        repo._col.find.assert_called_once_with(projection={"_id": 0})

    def test_get_unindexed_signatures(self, repo, mocker):
        """Get unindexed signatures."""
        cursor_mock = repo._col.find.return_value
        cursor_mock.__iter__ = lambda self: iter(
            [
                {
                    "sample_id": "sample_1",
                    "kmer_size": 21,
                    "signature_checksum": "check_abc",
                    "file_checksum": "file_abc",
                    "signature_path": "path/to/sig1",
                    "has_been_indexed": False,
                },
                {
                    "sample_id": "sample_1",
                    "kmer_size": 31,
                    "signature_checksum": "check_abc",
                    "file_checksum": "file_abc",
                    "signature_path": "path/to/sig1",
                    "has_been_indexed": False,
                },
            ]
        )
        cursor_mock.limit = repo._col.find.return_value.limit = mocker.MagicMock(
            return_value=cursor_mock
        )

        results = list(repo.get_unindexed_signatures(limit=10))

        assert len(results) == 2
        # Verify query filter
        repo._col.find.assert_called_once_with(
            {"has_been_indexed": False}, projection={"_id": 0}
        )
        cursor_mock.limit.assert_called_once_with(10)


class TestCountByChecksum:
    """Test count operations."""

    def test_count_by_checksum(self, repo):
        """Count signatures with matching checksum."""
        repo._col.count_documents.return_value = 3

        count = repo.count_by_checksum("check_abc")

        assert count == 3
        repo._col.count_documents.assert_called_once_with(
            {"signature_checksum": "check_abc"}
        )

    def test_count_by_checksum_zero(self, repo):
        """Count returns 0 when no matches."""
        repo._col.count_documents.return_value = 0

        count = repo.count_by_checksum("check_missing")

        assert count == 0


class TestFlagOperations:
    """Test flag update operations."""

    def test_mark_indexed_single_kmer(self, repo):
        """Mark specific sample as indexed."""
        repo._col.update_one.return_value.modified_count = 1

        result = repo.mark_indexed("sample_1")

        assert result is True
        # Verify update query
        call_args = repo._col.update_one.call_args
        query = call_args[0][0]
        assert query["sample_id"] == "sample_1"
        assert query["has_been_indexed"] == {"$ne": True}

    def test_mark_indexed_no_change(self, repo):
        """Mark indexed returns False if no modification."""
        repo._col.update_one.return_value.modified_count = 0

        result = repo.mark_indexed("sample_1")

        assert result is False

    def test_unmark_indexed(self, repo):
        """Unmark signature as indexed."""
        repo._col.update_one.return_value.modified_count = 1

        result = repo.unmark_indexed("sample_1")

        assert result is True

    def test_exclude_from_analysis(self, repo):
        """Exclude sample from analysis."""
        repo._col.update_one.return_value.modified_count = 1

        result = repo.exclude_from_analysis("sample_1")

        assert result is True

    def test_include_in_analysis(self, repo):
        """Include sample in analysis."""
        repo._col.update_one.return_value.modified_count = 1

        result = repo.include_in_analysis("sample_1")

        assert result is True

    def test_marked_for_deletion(self, repo):
        """Mark sample for deletion."""
        repo._col.update_one.return_value.modified_count = 1

        result = repo.marked_for_deletion("sample_1")

        assert result is True


class TestRemoveOperations:
    """Test deletion operations."""

    def test_remove_all_kmers_for_sample(self, repo):
        """Remove all kmer variants for a sample."""
        repo._col.delete_many.return_value.deleted_count = 3

        result = repo.remove_by_sample_id("sample_1")

        assert result == 3
        # Verify query
        call_args = repo._col.delete_many.call_args
        query = call_args[0][0]
        assert query == {"sample_id": "sample_1"}

    def test_remove_specific_kmer(self, repo):
        """Remove specific kmer variant."""
        repo._col.delete_many.return_value.deleted_count = 1

        result = repo.remove_by_sample_id("sample_1", kmer_size=21)

        assert result == 1
        # Verify query includes kmer_size
        call_args = repo._col.delete_many.call_args
        query = call_args[0][0]
        assert query["sample_id"] == "sample_1"
        assert query["kmer_size"] == 21

    def test_remove_not_found(self, repo):
        """Remove non-existent sample returns 0."""
        repo._col.delete_many.return_value.deleted_count = 0

        result = repo.remove_by_sample_id("nonexistent")

        assert result == 0


class TestIntegrationScenarios:
    """Integration tests for common workflows."""

    def test_workflow_add_multiple_kmers_query_separately(self, repo):
        """Add multiple kmers and query them separately."""
        # Setup mock for adds
        repo._col.insert_one.return_value.inserted_id = "id_123"

        # Add multiple kmers
        sig_21 = SignatureRecord(
            sample_id="sample_1",
            kmer_size=21,
            signature_path="path/sig_21",
            signature_checksum="check_abc",
            file_checksum="file_abc",
        )
        sig_31 = SignatureRecord(
            sample_id="sample_1",
            kmer_size=31,
            signature_path="path/sig_31",
            signature_checksum="check_def",
            file_checksum="file_def",
        )

        repo.add_signature(sig_21)
        repo.add_signature(sig_31)

        # Verify both were added
        assert repo._col.insert_one.call_count == 2

    def test_workflow_remove_one_kmer_preserves_others(self, repo):
        """Removing one kmer variant doesn't affect others."""
        # Delete returns 1 (deleted one)
        repo._col.delete_many.return_value.deleted_count = 1

        # Remove kmer=21, should not affect kmer=31
        result = repo.remove_by_sample_id("sample_1", kmer_size=21)

        assert result == 1
        # Verify the specific kmer was targeted
        call_args = repo._col.delete_many.call_args
        query = call_args[0][0]
        assert query["kmer_size"] == 21

    def test_workflow_backward_compatibility_no_kmer_specified(self, repo):
        """Operations work when kmer_size not specified (backward compatible)."""
        repo._col.find.return_value.alive = True
        repo._col.find.return_value.__iter__ = lambda self: iter([])

        # Should work without kmer_size
        results = repo.get_by_sample_id_or_checksum(sample_id="sample_1")

        # Query should not include kmer_size filter
        call_args = repo._col.find.call_args
        query = call_args[0][0]
        assert "kmer_size" not in query
