"""Exercise real Sourmash indexes and searches with in-memory sample metadata."""

import hashlib
from unittest.mock import Mock

import pytest
import sourmash

from minhash_service.analysis.similarity import filter_search_results
from minhash_service.core.config import Settings
from minhash_service.integrity import checker
from minhash_service.integrity.report_model import InitiatorType
from minhash_service.signatures.index import create_index_store, get_index_path
from minhash_service.signatures.io import write_signatures
from minhash_service.signatures.models import IndexFormat, SignatureRecord
from minhash_service.tasks import handlers


@pytest.fixture(params=[IndexFormat.ROCKSDB, IndexFormat.SBT])
def collection(tmp_path, monkeypatch, request):
    settings = Settings(
        signature_dir=tmp_path, index_format=request.param, kmer_size=31
    )
    monkeypatch.setattr(handlers, "cnf", settings)
    records = {}
    signatures = []
    for group, count in enumerate([2, 3, 4]):
        mh = sourmash.MinHash(n=0, ksize=31, scaled=1)
        mh.add_many(range(1, 101 - group * 10))
        sig = sourmash.SourmashSignature(mh, name=f"group-{group}")
        signatures.append(sig)
        path = tmp_path / f"group-{group}.sig"
        write_signatures(path, sourmash.signature.save_signatures_to_json([sig]))
        for number in range(count):
            sid = f"sample-{group}-{number}"
            records[sid] = SignatureRecord(
                sample_id=sid,
                kmer_size=31,
                signature_checksum=sig.md5sum(),
                signature_path=path,
                file_checksum=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
    repo = Mock()
    repo.get_all_signatures.side_effect = lambda: iter(records.values())
    repo.get_by_sample_id_or_checksum.side_effect = (
        lambda sample_id=None, checksum=None, kmer_size=None: [
            r
            for r in records.values()
            if (kmer_size is None or r.kmer_size == kmer_size)
            and (
                (sample_id is not None and r.sample_id == sample_id)
                or (checksum is not None and r.signature_checksum == checksum)
            )
        ]
    )

    def set_indexed(sid, kmer_size, indexed):
        if sid not in records:
            return False
        records[sid].has_been_indexed = indexed
        return True

    repo.set_indexed.side_effect = set_indexed
    repo.marked_for_deletion.side_effect = (
        lambda sid: setattr(records[sid], "marked_for_deletion", True) or True
    )
    repo.remove_by_sample_id.side_effect = lambda sid: records.pop(sid)
    repo.count_by_checksum.side_effect = lambda checksum: sum(
        r.signature_checksum == checksum for r in records.values()
    )
    monkeypatch.setattr(handlers, "create_signature_repo", lambda: repo)
    monkeypatch.setattr(checker, "create_signature_repo", lambda: repo)
    monkeypatch.setattr(handlers, "create_audit_trail_repo", lambda: Mock())
    index = create_index_store(get_index_path(tmp_path, request.param), request.param)
    return settings, records, repo, index, signatures


def test_repair_and_repeated_additions(collection):
    settings, records, repo, index, signatures = collection
    stale_mh = sourmash.MinHash(n=0, ksize=31, scaled=1)
    stale_mh.add_many(range(1000, 1100))
    stale = sourmash.SourmashSignature(stale_mh, name="stale")
    index.replace_signatures([signatures[0], stale])  # stale entry and missing groups
    handlers.rebuild_index()
    handlers.add_to_index(list(records))
    handlers.add_to_index(list(records))
    fresh = create_index_store(index.index_path, settings.index_format)
    assert len(list(fresh.index.signatures())) == 3
    assert all(r.has_been_indexed for r in records.values())
    report = checker.check_signature_integrity(InitiatorType.USER, settings)
    assert not report.has_warnings
    if settings.index_format == IndexFormat.ROCKSDB:
        result = handlers.search_similar("sample-0-0", min_similarity=0.5)
        assert len(result["matches"]) == 9
        assert len({m["sample_id"] for m in result["matches"]}) == 9
        limited = handlers.search_similar("sample-0-0", limit=3)
        assert [m["sample_id"] for m in limited["matches"]] == [
            "sample-0-0",
            "sample-0-1",
            "sample-1-0",
        ]
        subset = handlers.search_similar("sample-0-0", subset_sample_ids=["sample-0-1"])
        assert [m["sample_id"] for m in subset["matches"]] == ["sample-0-1"]
        newick = handlers.find_similar_and_cluster("sample-0-0")
        assert all(sid in newick for sid in records)


def test_exclusion_preserves_shared_signature_then_removes_batch(collection):
    settings, records, repo, index, signatures = collection
    handlers.rebuild_index()
    records["sample-0-0"].exclude_from_analysis = True
    handlers.remove_from_index(["sample-0-0"])
    assert not records["sample-0-0"].has_been_indexed
    assert records["sample-0-1"].has_been_indexed
    assert not checker.check_signature_integrity(
        InitiatorType.USER, settings
    ).has_warnings
    records["sample-0-1"].exclude_from_analysis = True
    handlers.remove_from_index(["sample-0-0", "sample-0-1"])
    handlers.remove_from_index(["sample-0-0", "sample-0-1"])  # retry is safe
    fresh = create_index_store(index.index_path, settings.index_format)
    assert signatures[0].md5sum() not in fresh.list_signature_checksums()
    handlers.rebuild_index()
    assert (
        len(
            list(
                create_index_store(
                    index.index_path, settings.index_format
                ).index.signatures()
            )
        )
        == 2
    )


def test_deletion_keeps_other_sample_searchable(collection):
    settings, records, repo, index, signatures = collection
    handlers.rebuild_index()
    path = records["sample-0-0"].signature_path
    handlers.remove_signature("sample-0-0")
    assert path.exists()
    assert (
        signatures[0].md5sum()
        in create_index_store(
            index.index_path, settings.index_format
        ).list_signature_checksums()
    )


def test_empty_repair_clears_stale_index(collection):
    settings, records, repo, index, signatures = collection
    handlers.rebuild_index()
    for r in records.values():
        r.exclude_from_analysis = True
    handlers.rebuild_index()
    assert not create_index_store(
        index.index_path, settings.index_format
    ).list_signature_checksums()
    assert all(not r.has_been_indexed for r in records.values())


def test_invalid_input_does_not_replace_index(collection):
    settings, records, repo, index, signatures = collection
    handlers.rebuild_index()
    records["sample-0-0"].signature_checksum = "incorrect"
    with pytest.raises(ValueError, match="Invalid signature"):
        handlers.rebuild_index()
    assert (
        len(
            create_index_store(
                index.index_path, settings.index_format
            ).list_signature_checksums()
        )
        == 3
    )


def test_metadata_failure_is_reported(collection):
    settings, records, repo, index, signatures = collection
    repo.set_indexed.side_effect = lambda *args: False
    with pytest.raises(RuntimeError, match="Could not update index status"):
        handlers.rebuild_index()


def test_replacement_failure_restores_previous_rocksdb(collection, monkeypatch):
    settings, records, repo, index, signatures = collection
    if settings.index_format != IndexFormat.ROCKSDB:
        return
    handlers.rebuild_index()
    from minhash_service.signatures import index as index_module

    original = index_module.DiskRevIndex
    replacement = Mock(side_effect=RuntimeError("cannot reopen replacement"))
    replacement.create_from_sigs.side_effect = original.create_from_sigs
    with monkeypatch.context() as context:
        context.setattr(index_module, "DiskRevIndex", replacement)
        with pytest.raises(RuntimeError, match="cannot reopen replacement"):
            index.replace_signatures([signatures[0]])
    assert (
        len(
            create_index_store(
                index.index_path, settings.index_format
            ).list_signature_checksums()
        )
        == 3
    )


def test_repair_cli_dry_run_does_not_write(collection, monkeypatch):
    import importlib
    from click.testing import CliRunner

    cli = importlib.import_module("minhash_service.cli.main")
    settings, records, repo, index, signatures = collection
    monkeypatch.setattr(cli, "cnf", settings)
    monkeypatch.setattr(cli.MongoDB, "setup", lambda **kwargs: None)
    monkeypatch.setattr(cli, "create_signature_repo", lambda: repo)
    rebuild = Mock()
    monkeypatch.setattr(cli, "rebuild_index", rebuild)
    result = CliRunner().invoke(cli.main, ["recreate-index", "--dry-run"])
    assert result.exit_code == 0
    rebuild.assert_not_called()
    repo.set_indexed.assert_not_called()
    assert not index.index_path.exists()


def test_repair_cli_reports_failure(collection, monkeypatch):
    import importlib
    from click.testing import CliRunner

    cli = importlib.import_module("minhash_service.cli.main")
    settings, records, repo, index, signatures = collection
    monkeypatch.setattr(cli, "cnf", settings)
    monkeypatch.setattr(cli.MongoDB, "setup", lambda **kwargs: None)
    monkeypatch.setattr(cli, "create_signature_repo", lambda: repo)
    monkeypatch.setattr(
        cli, "rebuild_index", Mock(side_effect=RuntimeError("metadata update failed"))
    )
    result = CliRunner().invoke(cli.main, ["recreate-index", "--force"])
    assert result.exit_code != 0
    assert "metadata update failed" in result.output
    assert "successfully" not in result.output


@pytest.mark.parametrize("failure", ["index", "file", "metadata"])
def test_deletion_failure_retains_metadata_and_can_retry(collection, monkeypatch, failure):
    from minhash_service.core.exceptions import FileRemovalError
    from minhash_service.signatures.index import RemoveResult
    from minhash_service.signatures.storage import SignatureStorage

    settings, records, repo, index, signatures = collection
    handlers.rebuild_index()
    handlers.remove_signature("sample-0-0")
    sid = "sample-0-1"
    path = records[sid].signature_path
    with monkeypatch.context() as patch:
        if failure == "index":
            failed_index = create_index_store(index.index_path, settings.index_format)
            patch.setattr(failed_index, "remove_signatures", lambda _: RemoveResult(
                is_successful=False, warnings=["failed"], removed_count=0, removed=[]
            ))
            patch.setattr(handlers, "create_index_store", lambda *a, **kw: failed_index)
        elif failure == "file":
            patch.setattr(SignatureStorage, "move_to_trash", Mock(side_effect=OSError("failed")))
        else:
            repo.remove_by_sample_id.side_effect = OSError("failed")
        with pytest.raises(FileRemovalError):
            handlers.remove_signature(sid)
    assert sid in records
    assert records[sid].marked_for_deletion
    if failure == "metadata":
        assert not path.exists()
        # Cleanup must retain the staged file even beyond its normal retention.
        import datetime as dt
        store = SignatureStorage(settings.signature_dir, settings.trash_dir)
        assert store.purge_older_than(
            dt.datetime.now(dt.UTC) + dt.timedelta(days=30),
            protected_paths={str(path)},
        ) == 0
    repo.remove_by_sample_id.side_effect = lambda sid: records.pop(sid)
    handlers.remove_signature(sid)
    assert sid not in records
    assert not path.exists()
    assert signatures[0].md5sum() not in create_index_store(
        index.index_path, settings.index_format
    ).list_signature_checksums()


@pytest.mark.parametrize("mutation", ["import", "qc", "delete"])
def test_rebuild_serializes_concurrent_mutations(collection, monkeypatch, mutation):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    settings, records, repo, index, signatures = collection
    snapshot = Event()
    resume = Event()
    started = Event()
    original_read = handlers.read_signatures

    def paused_read(*args, **kwargs):
        if not snapshot.is_set():
            snapshot.set()
            assert resume.wait(10)
        return original_read(*args, **kwargs)

    monkeypatch.setattr(handlers, "read_signatures", paused_read)
    repo.exclude_from_analysis.side_effect = lambda sid: setattr(
        records[sid], "exclude_from_analysis", True
    ) or True

    def mutate():
        started.set()
        if mutation == "import":
            handlers.add_signature("new-sample", sourmash.signature.save_signatures_to_json([signatures[0]]).decode())
            handlers.add_to_index(["new-sample"])
        elif mutation == "qc":
            handlers.exclude_from_analysis(["sample-0-0", "sample-0-1"])
            handlers.remove_from_index(["sample-0-0", "sample-0-1"])
        else:
            handlers.remove_signature("sample-0-0")
            handlers.remove_signature("sample-0-1")

    repo.add_signature.side_effect = lambda rec: records.setdefault(rec.sample_id, rec)
    with ThreadPoolExecutor(max_workers=2) as pool:
        rebuild = pool.submit(handlers.rebuild_index)
        assert snapshot.wait(10)
        update = pool.submit(mutate)
        assert started.wait(10)
        try:
            with pytest.raises(TimeoutError):
                update.result(timeout=0.1)
            assert "new-sample" not in records
            assert not records["sample-0-0"].exclude_from_analysis
            assert not records["sample-0-0"].marked_for_deletion
        finally:
            resume.set()
        rebuild.result(timeout=20)
        update.result(timeout=20)
    assert not checker.check_signature_integrity(InitiatorType.USER, settings).has_warnings


def test_workflow_lock_excludes_other_processes(tmp_path):
    import subprocess
    import sys
    from minhash_service.signatures.locking import signature_workflow_lock

    script = (
        "import fasteners, sys; "
        "lock = fasteners.InterProcessLock(sys.argv[1]); "
        "acquired = lock.acquire(blocking=False); "
        "print(acquired); "
        "lock.release() if acquired else None"
    )
    args = [sys.executable, "-c", script, str(tmp_path / ".signature-workflow.lock")]
    with signature_workflow_lock(tmp_path):
        assert subprocess.check_output(args, text=True).strip() == "False"
    assert subprocess.check_output(args, text=True).strip() == "True"


def test_default_trash_is_shared_and_persistent(tmp_path):
    first = Settings(signature_dir=tmp_path)
    second = Settings(signature_dir=tmp_path)
    assert first.trash_dir == second.trash_dir == tmp_path / "trash"


def test_deletion_stages_file_shared_by_multiple_sketches_once(collection):
    from minhash_service.core.exceptions import FileRemovalError

    settings, records, repo, index, signatures = collection
    handlers.rebuild_index()
    handlers.remove_signature("sample-0-0")
    sid = "sample-0-1"
    extra = records[sid].model_copy(update={"kmer_size": 51, "signature_checksum": "other-sketch"})
    def mark_all(sample_id):
        records[sample_id].marked_for_deletion = True
        extra.marked_for_deletion = True
        return True

    repo.marked_for_deletion.side_effect = mark_all
    lookup = repo.get_by_sample_id_or_checksum.side_effect
    repo.get_by_sample_id_or_checksum.side_effect = lambda sample_id=None, checksum=None, kmer_size=None: (
        [records[sid], extra] if sample_id == sid and kmer_size is None
        else lookup(sample_id, checksum, kmer_size)
    )
    repo.remove_by_sample_id.side_effect = OSError("metadata unavailable")
    with pytest.raises(FileRemovalError):
        handlers.remove_signature(sid)
    # MongoDB may return the sketches in a different order on retry.
    repo.get_by_sample_id_or_checksum.side_effect = lambda sample_id=None, checksum=None, kmer_size=None: (
        [extra, records[sid]] if sample_id == sid and kmer_size is None
        else lookup(sample_id, checksum, kmer_size)
    )
    repo.remove_by_sample_id.side_effect = lambda sample_id: records.pop(sample_id)
    handlers.remove_signature(sid)
    assert sid not in records
    assert not extra.signature_path.exists()
