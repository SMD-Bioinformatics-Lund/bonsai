"""Test MinHash task result and index bookkeeping helpers."""

from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from minhash_service.analysis.models import SimilarResult
from minhash_service.signatures.index import AddResult
from minhash_service.tasks.handlers import (
    _lookup_checksums_from_sample_ids,
    _resolve_sample_matches,
    add_to_index,
    remove_signature,
)


def _match(checksum: str, similarity: float = 0.95) -> SimilarResult:
    return SimilarResult(
        name=checksum,
        md5=checksum,
        containment=similarity,
        jaccard_similarity=similarity,
        max_containment=similarity,
    )


def _record(
    sample_id: str,
    checksum: str,
    *,
    excluded: bool = False,
    deleted: bool = False,
):
    return SimpleNamespace(
        sample_id=sample_id,
        signature_checksum=checksum,
        exclude_from_analysis=excluded,
        marked_for_deletion=deleted,
        kmer_size=31,
        signature_path=Mock(),
    )


def test_resolve_sample_matches_expands_shared_checksums():
    """Each eligible sample sharing a matched checksum is returned once."""
    repo = Mock()
    repo.get_by_sample_id_or_checksum.side_effect = lambda checksum, kmer_size: {
        "checksum-a": [
            _record("sample-b", checksum),
            _record("sample-a", checksum),
        ],
        "checksum-b": [
            _record("sample-c", checksum),
            _record("sample-excluded", checksum, excluded=True),
        ],
    }[checksum]

    resolved = _resolve_sample_matches(
        [_match("checksum-a"), _match("checksum-a"), _match("checksum-b")],
        repo,
        kmer_size=31,
    )

    assert [match.sample_id for match in resolved] == [
        "sample-a",
        "sample-b",
        "sample-c",
    ]


def test_resolve_sample_matches_applies_subset_and_sample_limit():
    """Subset filtering and limits operate on expanded sample IDs."""
    repo = Mock()
    repo.get_by_sample_id_or_checksum.return_value = [
        _record("sample-a", "checksum-a"),
        _record("sample-b", "checksum-a"),
        _record("sample-c", "checksum-a"),
    ]

    resolved = _resolve_sample_matches(
        [_match("checksum-a")],
        repo,
        kmer_size=31,
        subset_sample_ids=["sample-b", "sample-c"],
        limit=1,
    )

    assert [match.sample_id for match in resolved] == ["sample-b"]


def test_lookup_checksums_handles_multiple_records_and_deduplicates():
    """Sample subsets are converted to unique signature checksums."""
    repo = Mock()
    repo.get_by_sample_id_or_checksum.side_effect = [
        [_record("sample-a", "checksum-a")],
        [_record("sample-b", "checksum-a")],
    ]

    checksums = _lookup_checksums_from_sample_ids(["sample-a", "sample-b"], repo)

    assert checksums == ["checksum-a"]


def test_add_to_index_marks_all_samples_sharing_a_checksum():
    """Every indexed sample is marked, even when checksums are shared."""
    repo = Mock()
    records = {
        "sample-a": [_record("sample-a", "checksum-a")],
        "sample-b": [_record("sample-b", "checksum-a")],
    }
    repo.get_by_sample_id_or_checksum.side_effect = (
        lambda sample_id, kmer_size: records[sample_id]
    )
    index = Mock()
    index.add_signatures.return_value = AddResult(
        is_successful=True,
        warnings=[],
        added_count=1,
        added_md5s=["checksum-a"],
    )

    with (
        patch(
            "minhash_service.tasks.handlers.create_signature_repo",
            return_value=repo,
        ),
        patch(
            "minhash_service.tasks.handlers._load_signatures_from_sample_id",
            return_value=[Mock()],
        ),
        patch(
            "minhash_service.tasks.handlers.create_index_store",
            return_value=index,
        ),
    ):
        add_to_index(["sample-a", "sample-b"])

    assert repo.set_indexed.call_args_list == [
        call("sample-a", 31, True),
        call("sample-b", 31, True),
    ]


def test_remove_signature_keeps_shared_checksum_indexed():
    """Deleting one sample preserves a checksum still used by another sample."""
    repo = Mock()
    repo.marked_for_deletion.return_value = True
    record = _record("sample-a", "checksum-a", deleted=True)
    other = _record("sample-b", "checksum-a")
    other.signature_path = record.signature_path
    repo.get_by_sample_id_or_checksum.return_value = [record]
    repo.get_all_signatures.return_value = [other]
    index = Mock()
    store = Mock()
    audit = Mock()

    with (
        patch(
            "minhash_service.tasks.handlers.create_signature_repo",
            return_value=repo,
        ),
        patch(
            "minhash_service.tasks.handlers.create_index_store",
            return_value=index,
        ),
        patch(
            "minhash_service.tasks.handlers.SignatureStorage",
            return_value=store,
        ),
        patch(
            "minhash_service.tasks.handlers.create_audit_trail_repo",
            return_value=audit,
        ),
    ):
        result = remove_signature("sample-a")

    assert result["is_successful"] is True
    index.remove_signatures.assert_not_called()
    store.move_to_trash.assert_not_called()
