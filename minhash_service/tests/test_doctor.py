"""Check physical index membership, exclusions and shared signatures."""

from unittest.mock import Mock

import pytest
import sourmash
from redis import Redis
from rq.job import Job

from minhash_service import doctor
from minhash_service.core.config import Settings
from minhash_service.signatures.index import create_index_store
from minhash_service.signatures.models import IndexFormat, SignatureRecord
from minhash_service.tasks.dispatch import ALLOWED_ENTRYPOINTS


@pytest.fixture(params=[IndexFormat.ROCKSDB, IndexFormat.SBT])
def data(tmp_path, monkeypatch, request):
    settings = Settings(signature_dir=tmp_path, index_format=request.param)
    monkeypatch.setattr(doctor, "cnf", settings)
    path = tmp_path / "sample.sig"
    path.write_bytes(b"nonempty")
    mh = sourmash.MinHash(n=0, ksize=31, scaled=1)
    mh.add_many(range(1, 100))
    signature = sourmash.SourmashSignature(mh)
    records = [
        SignatureRecord(
            sample_id=sid,
            kmer_size=31,
            signature_path=path,
            file_checksum="unused",
            signature_checksum=signature.md5sum(),
            has_been_indexed=sid == "active",
            exclude_from_analysis=sid == "excluded",
        )
        for sid in ("active", "excluded")
    ]
    repo = Mock()
    repo.get_all_signatures.side_effect = lambda: iter(records)
    monkeypatch.setattr(doctor, "create_signature_repo", lambda: repo)
    (tmp_path / "indexes").mkdir()
    index_path = tmp_path / "indexes" / f"genomes_{request.param.value.lower()}_index"
    index = create_index_store(index_path, request.param)
    index.replace_signatures([signature])
    return records, index


def test_excluded_sample_can_share_a_signature_with_an_active_sample(data):
    job = Job.create(
        "minhash_service.tasks.dispatch_job",
        kwargs={
            "task": "doctor_check_samples",
            "samples": [{"sample_id": "excluded", "qc_failed": True}],
        },
        connection=Redis(),
    )
    assert job.func_name in ALLOWED_ENTRYPOINTS
    result = job.func(*job.args, **job.kwargs)
    assert result == {"findings": [], "errors": []}


def test_qc_failure_with_stale_exclusion_flags_is_reported(data):
    records, _ = data
    records[0].has_been_indexed = False
    records[1].marked_for_deletion = True
    result = doctor.check_samples([{"sample_id": "active", "qc_failed": True}])
    messages = [finding["message"] for finding in result["findings"]]
    assert "QC-failed signature is not excluded from analysis" in messages
    assert "QC-failed signature remains indexed" in messages


def test_actual_membership_is_checked_even_when_metadata_says_indexed(data):
    records, index = data
    index.replace_signatures([])
    result = doctor.check_samples([{"sample_id": "active", "qc_failed": False}])
    assert any(
        "missing from the search index" in f["message"] for f in result["findings"]
    )
    assert records[0].has_been_indexed  # Doctor never repairs metadata.


def test_missing_files_and_metadata_are_reported(data):
    records, _ = data
    records[0].signature_path.unlink()
    result = doctor.check_samples(
        [{"sample_id": sid, "qc_failed": False} for sid in ("active", "absent")]
    )
    assert {f["sample_id"] for f in result["findings"]} == {"active", "absent"}
    assert not result["errors"]


def test_unreadable_index_preserves_file_findings(data, monkeypatch):
    records, _ = data
    records[0].signature_path.write_bytes(b"")
    monkeypatch.setattr(
        doctor,
        "create_index_store",
        Mock(side_effect=PermissionError("unreadable index")),
    )
    result = doctor.check_samples([{"sample_id": "active", "qc_failed": False}])
    assert result["errors"]
    assert any("empty" in f["message"] for f in result["findings"])
