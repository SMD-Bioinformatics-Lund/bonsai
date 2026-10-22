"""Doctor checks all samples and never reports a partial check as clean."""

import importlib
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from click.testing import CliRunner
from mongomock_motor import AsyncMongoMockClient

from bonsai_api import doctor
from bonsai_api.cli.cli import cli

doctor_cli = importlib.import_module("bonsai_api.cli.doctor")


@pytest.fixture
def database(monkeypatch):
    collection = AsyncMongoMockClient().db.samples

    @asynccontextmanager
    async def connect():
        yield SimpleNamespace(sample_collection=collection)

    monkeypatch.setattr(doctor, "get_db_connection", connect)
    monkeypatch.setattr(
        doctor, "check_worker", AsyncMock(return_value={"findings": [], "errors": []})
    )
    return collection


def sample(sid, assay="wgs"):
    return {
        "sample_id": sid,
        "external_sample_id": f"lab-{sid}",
        "lims_id": f"lims-{sid}",
        "last_pipeline_run_id": "current",
        "pipeline_runs": [
            {"pipeline_run_id": "old", "assay": "old-assay"},
            {"pipeline_run_id": "current", "assay": assay},
        ],
    }


@pytest.mark.asyncio
async def test_all_records_are_checked_without_pagination(database):
    await database.insert_many([sample(str(i)) for i in range(125)])
    report = await doctor.run_check()
    assert report.checked_samples == report.affected_samples == 125
    assert report.exit_code == 1
    assert await database.count_documents({}) == 125


@pytest.mark.asyncio
async def test_all_assays_and_samples_are_checked(database):
    await database.insert_many([sample("one"), sample("two", "other")])
    report = await doctor.run_check()
    assert report.checked_samples == 2
    assert {f.sample_id for f in report.findings} == {"one", "two"}
    assert {f.assay for f in report.findings} == {"wgs", "other"}
    for sid in ("one", "two"):
        assert {f.file_type for f in report.findings if f.sample_id == sid} == {
            "alignment",
            "ska",
            "minhash",
        }
    assert report.exit_code == 1


def test_alignment_uses_current_resources_and_checks_index(tmp_path, monkeypatch):
    monkeypatch.setattr(doctor.settings, "annotations_dir", str(tmp_path))
    (tmp_path / "reads.bam").write_bytes(b"nonempty")
    doc = {"genomic_resources": [{"type": "alignment", "path": "reads.bam"}]}
    assert [f["file_type"] for f in doctor.check_alignment(doc)] == ["alignment-index"]
    (tmp_path / "reads.bam.bai").touch()
    doc["genomic_resources"][0]["index_path"] = "reads.bam.bai"
    assert doctor.check_alignment(doc)[0]["message"] == "File is empty"
    (tmp_path / "reads.bam.bai").write_bytes(b"index")
    assert doctor.check_alignment(doc) == []
    (tmp_path / "reads.bam").unlink()
    assert [f["file_type"] for f in doctor.check_alignment(doc)] == ["alignment"]


@pytest.mark.asyncio
async def test_worker_errors_leave_local_findings_visible(database, monkeypatch):
    doc = sample("one")
    doc.update(
        ska_index="one.skf",
        genome_signature="signature.sig",
        qc_status={"status": "failed"},
    )
    await database.insert_one(doc)
    worker = AsyncMock(return_value={"findings": [], "errors": ["worker unavailable"]})
    monkeypatch.setattr(doctor, "check_worker", worker)
    report = await doctor.run_check()
    assert report.exit_code == 2
    assert report.affected_samples == 1  # Missing alignment is still reported.
    assert worker.await_count == 2
    assert worker.await_args_list[1].args[1][0]["qc_failed"] is True


@pytest.mark.asyncio
async def test_worker_findings_keep_sample_labels_and_assay(database, monkeypatch):
    doc = sample("one")
    doc["ska_index"] = "one.skf"
    await database.insert_one(doc)
    monkeypatch.setattr(
        doctor,
        "check_worker",
        AsyncMock(
            return_value={
                "findings": [
                    {
                        "sample_id": "one",
                        "file_type": "ska",
                        "message": "File is missing",
                        "path": "one.skf",
                    }
                ],
                "errors": [],
            }
        ),
    )
    report = await doctor.run_check()
    assert report.exit_code == 1
    finding = next(f for f in report.findings if f.file_type == "ska")
    assert finding.external_sample_id == "lab-one"
    assert finding.assay == "wgs"


@pytest.mark.asyncio
async def test_finished_worker_returns_serializable_report(monkeypatch):
    result = {"findings": [], "errors": []}
    job = SimpleNamespace(
        get_status=lambda **kw: "finished", return_value=lambda: result
    )
    enqueue = SimpleNamespace(enqueue=lambda *a, **kw: job)
    monkeypatch.setattr(doctor, "Queue", lambda *a, **kw: enqueue)
    assert await doctor.check_worker("ska", [{"sample_id": "one"}], 10) == result


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["failed", "canceled", "stopped", "queued"])
async def test_worker_failure_and_timeout_are_incomplete(monkeypatch, status):
    job = SimpleNamespace(id="job", get_status=lambda **kw: status)
    monkeypatch.setattr(
        doctor, "Queue", lambda *a, **kw: SimpleNamespace(enqueue=lambda *a, **kw: job)
    )
    result = await doctor.check_worker("ska", [{"sample_id": "one"}], timeout=0.01)
    assert result["errors"]
    assert not result["findings"]


@pytest.mark.parametrize(
    "errors,findings,expected",
    [
        ([], [], 0),
        ([], [True], 1),
        (["unavailable"], [True], 2),
        (["unavailable"], [], 2),
    ],
)
def test_report_and_exit_status(monkeypatch, errors, findings, expected):
    report = doctor.DoctorReport(
        checked_samples=1,
        errors=errors,
        findings=[
            doctor.Finding(
                sample_id="one", assay="wgs", file_type="ska", message="Missing"
            )
            for _ in findings
        ],
    )
    check = AsyncMock(return_value=report)
    monkeypatch.setattr(doctor_cli, "run_check", check)
    result = CliRunner().invoke(cli, ["doctor"])
    assert result.exit_code == expected, result.output
    check.assert_awaited_once_with()
    if expected == 0:
        assert result.output == "No issues found\n"
    else:
        assert "No issues found" not in result.output
        if findings:
            assert "sample=one" in result.output
            assert "ska: Missing" in result.output
        if errors:
            assert "Check incomplete: unavailable" in result.output


def test_database_failure_is_reported(monkeypatch):
    monkeypatch.setattr(
        doctor_cli,
        "run_check",
        AsyncMock(side_effect=RuntimeError("database unavailable")),
    )
    result = CliRunner().invoke(cli, ["doctor"])
    assert result.exit_code == 2
    assert "database unavailable" in result.output
    assert "No issues found" not in result.output
