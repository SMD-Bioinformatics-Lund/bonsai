"""Doctor must not report a clean result after partial or filtered checks."""

import importlib
import json
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
    monkeypatch.setattr(doctor.settings, "doctor_assay_requirements", {})
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
    report = await doctor.run_check(file_types=("alignment",))
    assert report.checked_samples == report.affected_samples == 125
    assert report.exit_code == 1
    assert await database.count_documents({}) == 125


@pytest.mark.asyncio
async def test_current_assay_and_sample_filters_intersect(database):
    await database.insert_many([sample("one"), sample("two", "other")])
    report = await doctor.run_check(
        assays=("wgs",), sample_ids=("lab-one",), file_types=("ska",)
    )
    assert report.checked_samples == 1
    assert [f.sample_id for f in report.findings] == ["one"]
    historical = await doctor.run_check(
        assays=("old-assay",), file_types=("alignment",)
    )
    assert historical.checked_samples == 0
    assert historical.exit_code == 2


@pytest.mark.asyncio
async def test_assay_requirements_and_missing_requested_samples(database, monkeypatch):
    await database.insert_one(sample("one", "amplicon"))
    monkeypatch.setattr(
        doctor.settings, "doctor_assay_requirements", {"amplicon": ["alignment"]}
    )
    report = await doctor.run_check(sample_ids=("one", "absent"))
    assert [f.file_type for f in report.findings] == ["alignment"]
    assert "absent" in report.errors[0]
    assert report.exit_code == 2


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
    report = await doctor.run_check(file_types=("ska",))
    assert report.exit_code == 1
    assert report.findings[0].external_sample_id == "lab-one"
    assert report.findings[0].assay == "wgs"


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
    [([], [], 0), ([], [True], 1), (["unavailable"], [True], 2)],
)
@pytest.mark.parametrize("group_by", ["sample", "file-type"])
def test_json_grouping_and_exit_status(
    monkeypatch, errors, findings, expected, group_by
):
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
    result = CliRunner().invoke(
        cli,
        [
            "doctor",
            "check",
            "--assay",
            "wgs",
            "--assay",
            "other",
            "--format",
            "json",
            "--group-by",
            group_by,
        ],
    )
    assert result.exit_code == expected, result.output
    payload = json.loads(result.output)
    assert payload["affected_samples"] == len(findings)
    assert set(payload["groups"]) == (
        {"one" if group_by == "sample" else "ska"} if findings else set()
    )
    assert check.await_args.kwargs["assays"] == ("wgs", "other")


def test_database_failure_produces_a_json_report(monkeypatch):
    monkeypatch.setattr(
        doctor_cli,
        "run_check",
        AsyncMock(side_effect=RuntimeError("database unavailable")),
    )
    result = CliRunner().invoke(cli, ["doctor", "check", "--format", "json"])
    assert result.exit_code == 2
    assert "database unavailable" in json.loads(result.output)["errors"][0]
