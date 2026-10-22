"""Test MinHash task result and index bookkeeping helpers."""

from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import pytest

from minhash_service.analysis.models import SimilarResult
from minhash_service.core.exceptions import SignatureNotFoundError
from minhash_service.signatures.index import AddResult
from minhash_service.signatures.io import read_signatures
from minhash_service.tasks.handlers import (
    _lookup_checksums_from_sample_ids,
    _load_signatures_from_sample_id,
    _resolve_sample_matches,
    add_to_index,
    check_signature,
    cluster_samples,
    find_similar_and_cluster,
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


def test_remove_signature_without_a_signature_is_a_no_op():
    """A sample uploaded without a signature can still be deleted."""
    repo = Mock()
    repo.get_by_sample_id_or_checksum.return_value = []
    index = Mock()

    with (
        patch(
            "minhash_service.tasks.handlers.create_signature_repo", return_value=repo
        ),
        patch("minhash_service.tasks.handlers.create_index_store", return_value=index),
        patch("minhash_service.tasks.handlers.SignatureStorage"),
        patch("minhash_service.tasks.handlers.create_audit_trail_repo"),
    ):
        result = remove_signature("sample-without-signature")

    assert result["is_successful"] is True
    assert result["removed_count"] == 0
    index.remove_signatures.assert_not_called()
    repo.marked_for_deletion.assert_not_called()


@pytest.mark.parametrize("repeat_sample", [False, True])
def test_cluster_samples_labels_samples_sharing_a_signature(data_dir, repeat_sample):
    """Samples with an identical sketch each keep their own leaf label."""
    paths = {
        "sample-a": data_dir / "DRR237260.sig",
        "sample-b": data_dir / "DRR237260.sig",
        "sample-c": data_dir / "DRR237261.sig",
    }
    repo = Mock()
    repo.get_by_sample_id_or_checksum.side_effect = lambda sample_id, kmer_size: [
        SimpleNamespace(
            signature_path=paths[sample_id],
            signature_checksum=read_signatures(paths[sample_id], kmer_size=kmer_size)[
                0
            ].md5sum(),
            exclude_from_analysis=False,
            marked_for_deletion=False,
        )
    ]

    with (
        patch(
            "minhash_service.tasks.handlers.create_signature_repo", return_value=repo
        ),
        patch("minhash_service.tasks.handlers.signature_workflow_lock"),
    ):
        sample_ids = list(paths) + (["sample-a"] if repeat_sample else [])
        newick = cluster_samples(sample_ids)

    for sample_id in paths:
        assert newick.count(f"{sample_id}:") == 1


@pytest.mark.parametrize(
    "problem,reason",
    [
        ("missing", "no signature for k-mer size"),
        ("duplicate", "multiple signature records"),
        ("excluded", "excluded from analysis"),
        ("deleting", "marked for deletion"),
        ("missing_file", "signature file missing, unreadable, or invalid"),
        ("invalid_file", "signature file missing, unreadable, or invalid"),
        ("wrong_kmer", "signature file missing, unreadable, or invalid"),
        ("empty", "expected exactly one signature"),
        ("multiple", "expected exactly one signature"),
        ("checksum", "signature does not match its record"),
    ],
)
def test_cluster_samples_rejects_incomplete_input(data_dir, problem, reason):
    """Two valid samples must never produce a partial tree when a third is invalid."""
    signature = read_signatures(data_dir / "DRR237260.sig", kmer_size=31)[0]
    good = _record("good", signature.md5sum())
    bad = _record("bad", signature.md5sum())
    bad.signature_path = "bad.sig"
    bad.exclude_from_analysis = problem == "excluded"
    bad.marked_for_deletion = problem == "deleting"
    if problem == "checksum":
        bad.signature_checksum = "wrong-checksum"

    def load(path, kmer_size):
        if path != "bad.sig":
            return [signature]
        if problem == "missing_file":
            raise FileNotFoundError("server/path/bad.sig")
        if problem == "invalid_file":
            raise ValueError("invalid signature")
        if problem == "wrong_kmer":
            raise SignatureNotFoundError("no matching k-mer size")
        if problem == "empty":
            return []
        return [signature, signature] if problem == "multiple" else [signature]

    repo = Mock()
    records = (
        [] if problem == "missing" else [bad, bad] if problem == "duplicate" else [bad]
    )
    repo.get_by_sample_id_or_checksum.side_effect = lambda sample_id, kmer_size: (
        records if sample_id == "bad" else [good]
    )

    with (
        patch(
            "minhash_service.tasks.handlers.create_signature_repo", return_value=repo
        ),
        patch("minhash_service.tasks.handlers.read_signatures", side_effect=load),
        patch("minhash_service.tasks.handlers.cluster_signatures") as cluster,
    ):
        with pytest.raises(ValueError, match="Cannot cluster samples") as error:
            cluster_samples(
                ["good-a", "good-b", "bad"], sample_labels={"bad": "LAB-123"}
            )

    assert f"LAB-123 ({reason}" in str(error.value)
    assert "server/path" not in str(error.value)
    cluster.assert_not_called()
    assert repo.get_by_sample_id_or_checksum.call_args.kwargs == {
        "sample_id": "bad",
        "kmer_size": 31,
    }


def test_cluster_samples_reports_all_unavailable_samples():
    """An error lists every missing sample, falling back to its internal ID."""
    repo = Mock()
    repo.get_by_sample_id_or_checksum.return_value = []
    with patch(
        "minhash_service.tasks.handlers.create_signature_repo", return_value=repo
    ):
        with pytest.raises(ValueError) as error:
            cluster_samples(
                ["missing-a", "missing-b"], sample_labels={"missing-a": "LAB-A"}
            )

    assert "LAB-A (no signature" in str(error.value)
    assert "missing-b (no signature" in str(error.value)


def test_cluster_samples_rejects_multiple_sketches_masking_a_missing_sample(data_dir):
    """Matching total sketch counts cannot hide an omitted sample."""
    signature = read_signatures(data_dir / "DRR237260.sig", kmer_size=31)[0]
    repo = Mock()
    repo.get_by_sample_id_or_checksum.side_effect = lambda sample_id, kmer_size: (
        [] if sample_id == "missing" else [_record(sample_id, signature.md5sum())]
    )
    with (
        patch(
            "minhash_service.tasks.handlers.create_signature_repo", return_value=repo
        ),
        patch(
            "minhash_service.tasks.handlers.read_signatures",
            return_value=[signature, signature],
        ),
        patch("minhash_service.tasks.handlers.cluster_signatures") as cluster,
    ):
        with pytest.raises(ValueError) as error:
            cluster_samples(["multiple", "missing"])

    assert "multiple (expected exactly one signature" in str(error.value)
    assert "missing (no signature" in str(error.value)
    cluster.assert_not_called()


@pytest.mark.parametrize("sample_ids", [[], ["only"], ["only", "only"]])
def test_cluster_samples_requires_two_distinct_samples(sample_ids):
    with patch("minhash_service.tasks.handlers.create_signature_repo") as repo:
        with pytest.raises(ValueError, match="at least two distinct samples"):
            cluster_samples(sample_ids)
    repo.assert_not_called()


def test_index_signature_loading_still_filters_ineligible_samples(data_dir):
    """Strict clustering validation does not change the indexing loader."""
    signature = read_signatures(data_dir / "DRR237260.sig", kmer_size=31)[0]
    good = _record("good", signature.md5sum())
    excluded = _record("excluded", signature.md5sum(), excluded=True)
    repo = Mock()
    repo.get_by_sample_id_or_checksum.side_effect = lambda sample_id, kmer_size: {
        "good": [good],
        "excluded": [excluded],
        "missing": [],
    }[sample_id]
    with (
        patch(
            "minhash_service.tasks.handlers.create_signature_repo", return_value=repo
        ),
        patch(
            "minhash_service.tasks.handlers.read_signatures", return_value=[signature]
        ),
    ):
        loaded = _load_signatures_from_sample_id(["good", "excluded", "missing"], 31)
    assert loaded == [signature]


def test_similar_clustering_rejects_a_match_that_became_unavailable(data_dir):
    """Search filtering does not allow a partial tree if a match disappears later."""
    signature = read_signatures(data_dir / "DRR237260.sig", kmer_size=31)[0]
    repo = Mock()
    repo.get_by_sample_id_or_checksum.side_effect = lambda sample_id, kmer_size: (
        [] if sample_id == "gone" else [_record(sample_id, signature.md5sum())]
    )
    with (
        patch(
            "minhash_service.tasks.handlers.create_signature_repo", return_value=repo
        ),
        patch(
            "minhash_service.tasks.handlers.read_signatures", return_value=[signature]
        ),
        patch(
            "minhash_service.tasks.handlers.search_similar",
            return_value={
                "matches": [{"sample_id": sid} for sid in ["good-a", "good-b", "gone"]]
            },
        ),
        patch("minhash_service.tasks.handlers.cluster_signatures") as cluster,
    ):
        with pytest.raises(ValueError, match="gone .*no signature"):
            find_similar_and_cluster("good-a")

    cluster.assert_not_called()


def test_check_signature_reports_the_signature_checksum(data_dir):
    path = data_dir / "DRR237260.sig"
    checksum = read_signatures(path)[0].md5sum()
    repo = Mock()
    repo.get_by_sample_id_or_checksum.return_value = [
        SimpleNamespace(
            signature_path=path, signature_checksum=checksum, has_been_indexed=True
        )
    ]

    with patch(
        "minhash_service.tasks.handlers.create_signature_repo", return_value=repo
    ):
        result = check_signature("sample-a")

    assert result["records"] == [
        {"exists": True, "checksum": checksum, "indexed": True}
    ]


def test_cron_schedules_the_integrity_check(settings, monkeypatch):
    """The periodic task must run the check, not only read the last report."""
    import importlib

    from click.testing import CliRunner

    cli = importlib.import_module("minhash_service.cli.main")
    cron = Mock()
    monkeypatch.setattr(cli, "cnf", settings)
    monkeypatch.setattr(cli, "Redis", Mock())
    monkeypatch.setattr(cli, "CronScheduler", Mock(return_value=cron))

    result = CliRunner().invoke(cli.main, ["run-cron-scheduler"])

    assert result.exit_code == 0, result.output
    tasks = [c.kwargs["kwargs"]["task"] for c in cron.register.call_args_list]
    assert "check_data_integrity" in tasks
    assert "get_integrity_report" not in tasks
    cron.start.assert_called_once()
