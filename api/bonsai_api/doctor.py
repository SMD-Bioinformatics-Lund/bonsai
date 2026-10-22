"""Read-only sample integrity checks for the API container CLI."""

import asyncio
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel, Field
from redis import Redis
from rq import Queue

from .config import settings
from .db.utils import get_db_connection
from .exceptions import GenomeResourceError
from .io import to_relative_resource


class Finding(BaseModel):
    """A resource problem with enough context to identify its sample."""

    sample_id: str
    external_sample_id: str | None = None
    lims_id: str | None = None
    assay: str | None = None
    file_type: str
    message: str
    path: str | None = None


class DoctorReport(BaseModel):
    """Keep detected problems separate from checks that could not complete."""

    checked_samples: int = 0
    findings: list[Finding] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @property
    def affected_samples(self) -> int:
        return len({finding.sample_id for finding in self.findings})

    @property
    def exit_code(self) -> int:
        return 2 if self.errors else (1 if self.findings else 0)


def current_assay(sample: dict) -> str | None:
    """Match the current pipeline selection used by sample summaries."""
    return next(
        (
            run.get("assay")
            for run in sample.get("pipeline_runs") or []
            if run.get("pipeline_run_id") == sample.get("last_pipeline_run_id")
        ),
        None,
    )


def check_alignment(sample: dict) -> list[dict]:
    """Check every registered alignment and index under the IGV data mount."""
    findings = []
    alignments = [
        r for r in sample.get("genomic_resources") or [] if r.get("type") == "alignment"
    ]
    if not alignments:
        return [
            {"file_type": "alignment", "message": "No alignment resource is registered"}
        ]
    for resource in alignments:
        for key, file_type in (
            ("path", "alignment"),
            ("index_path", "alignment-index"),
        ):
            path = resource.get(key)
            message = None
            if not path:
                message = "No file path is registered"
            else:
                try:
                    relative = to_relative_resource(
                        path, Path(settings.annotations_dir)
                    )
                    resolved = Path(settings.annotations_dir) / relative
                    if resolved.stat().st_size == 0:
                        message = "File is empty"
                except (GenomeResourceError, OSError, ValueError) as error:
                    message = f"File is missing, unreadable, or outside the configured directory: {error}"
            if message:
                findings.append(
                    {"file_type": file_type, "message": message, "path": path}
                )
    return findings


async def check_worker(queue_name: str, samples: list[dict], timeout: int) -> dict:
    """Enqueue one batch and wait with a bounded connection and job timeout."""
    connection = Redis(
        settings.redis_host,
        int(settings.redis_port),
        socket_timeout=5,
        socket_connect_timeout=5,
    )
    try:
        queue = Queue(queue_name, connection=connection)
        job = await asyncio.to_thread(
            queue.enqueue,
            f"{queue_name}_service.doctor.check_samples",
            samples=samples,
            job_timeout=timeout,
            ttl=timeout,
            result_ttl=60,
        )
        async with asyncio.timeout(timeout):
            while True:
                status = await asyncio.to_thread(job.get_status, refresh=True)
                if status == "finished":
                    result = await asyncio.to_thread(job.return_value)
                    if (
                        not isinstance(result, dict)
                        or not {"findings", "errors"} <= result.keys()
                    ):
                        raise ValueError("Worker returned an invalid doctor report")
                    return result
                if status in {"failed", "stopped", "canceled"}:
                    raise RuntimeError(
                        f"Worker job {job.id} {status}; inspect worker logs"
                    )
                await asyncio.sleep(0.25)
    except TimeoutError:
        return {
            "findings": [],
            "errors": [f"{queue_name} check timed out after {timeout}s"],
        }
    except Exception as error:
        return {
            "findings": [],
            "errors": [f"{queue_name} check could not complete: {error}"],
        }
    finally:
        connection.close()


async def run_check() -> DoctorReport:
    """Check every sample without pagination or full-model hydration."""
    report = DoctorReport()
    selected = {}
    batches = defaultdict(list)
    projection = {
        field: 1
        for field in (
            "sample_id",
            "external_sample_id",
            "lims_id",
            "pipeline_runs.assay",
            "pipeline_runs.pipeline_run_id",
            "last_pipeline_run_id",
            "genomic_resources",
            "ska_index",
            "genome_signature",
            "qc_status.status",
        )
    }
    async with get_db_connection() as db:
        async for sample in db.sample_collection.find({}, projection):
            assay = current_assay(sample)
            report.checked_samples += 1
            sid = sample.get("sample_id") or str(sample["_id"])
            context = {
                "sample_id": sid,
                "external_sample_id": sample.get("external_sample_id"),
                "lims_id": sample.get("lims_id"),
                "assay": assay,
            }
            selected[sid] = context
            report.findings.extend(
                Finding(**context, **issue) for issue in check_alignment(sample)
            )
            for file_type, field in (
                ("ska", "ska_index"),
                ("minhash", "genome_signature"),
            ):
                if not sample.get(field):
                    report.findings.append(
                        Finding(
                            **context,
                            file_type=file_type,
                            message="No resource reference is registered",
                        )
                    )
                if not sample.get("sample_id"):
                    report.errors.append(
                        f"Record {sid} has no sample_id; cannot check {file_type}"
                    )
                elif file_type == "ska" and sample.get(field):
                    batches["ska"].append(
                        {"sample_id": sid, "ska_index": sample[field]}
                    )
                elif file_type == "minhash":
                    batches["minhash"].append(
                        {
                            "sample_id": sid,
                            "qc_failed": (sample.get("qc_status") or {}).get("status")
                            == "failed",
                        }
                    )
    results = await asyncio.gather(
        *(check_worker(name, samples, timeout=60) for name, samples in batches.items())
    )
    for result in results:
        report.errors.extend(result["errors"])
        for issue in result["findings"]:
            context = selected[issue["sample_id"]]
            report.findings.append(
                Finding(
                    **context,
                    **{
                        key: value for key, value in issue.items() if key != "sample_id"
                    },
                )
            )
    report.findings.sort(
        key=lambda f: (f.sample_id, f.file_type, f.path or "", f.message)
    )
    return report
