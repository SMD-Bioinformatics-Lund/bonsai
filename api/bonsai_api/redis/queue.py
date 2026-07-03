"""Functions for managing redis connections."""

import logging
from datetime import datetime
from enum import StrEnum
from typing import Any

from bonsai_api.config import settings
from pydantic import BaseModel
from redis import Redis
from rq.job import Job

from bonsai_libs.jobs import configure_queue

LOG = logging.getLogger(__name__)


class JobFailedError(Exception):
    """Failed redis job."""


class RedisQueue:  # pylint: disable=too-few-public-methods
    """Worker queue interface."""

    def __init__(self) -> None:
        """Setup connection and define queues."""
        self.connection = Redis(settings.redis_host, int(settings.redis_port))
        self.minhash = configure_queue("minhash", connection=self.connection)
        self.ska = configure_queue("ska", connection=self.connection)
        self.allele = configure_queue("allele_cluster", connection=self.connection)


redis = RedisQueue()


class JobStatusCodes(StrEnum):
    """Container for RQ status codes"""

    QUEUED = "queued"
    STARTED = "started"
    DEFERRED = "deferred"
    FINISHED = "finished"
    STOPPED = "stopped"
    SCHEDULED = "scheduled"
    CANCELED = "canceled"
    FAILED = "failed"


class JobStatus(BaseModel):  # pylint: disable=too-few-public-methods
    """Container for basic job information."""

    status: JobStatusCodes
    queue: str
    task: str
    result: Any
    error: str | None = None
    submitted_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    task_status: str | None = None
    metadata: dict[str, Any] | None = None


def _extract_task_name(job: Job) -> str:
    """Extract the logical task name from the enqueued JobRequest payload."""
    if job.args:
        first_arg = job.args[0]
        if isinstance(first_arg, dict):
            task = first_arg.get("task")
            if isinstance(task, str):
                return task
    return job.func_name



def check_redis_job_status(job_id: str, raise_on_exception: bool = False) -> JobStatus:
    """Check status of a job."""
    job = Job.fetch(job_id, connection=redis.connection)
    rq_status = job.get_status(refresh=True)

    task_name = _extract_task_name(job)
    return_value = job.return_value()

    task_status = None
    result = None
    error = None
    metadata = None

    if isinstance(return_value, dict) and "error" in return_value:
        task_status = return_value.get("status")
        result = return_value.get("result")
        error = return_value.get("error")
        metadata = return_value.get("metadata")
    else:
        result = return_value

    job_info = JobStatus(
        status=rq_status,
        queue=job.origin,
        task=task_name,
        result=result,
        submitted_at=job.enqueued_at,
        started_at=job.started_at,
        finished_at=job.ended_at,
        task_status=task_status,
        error=error,
        metadata=metadata
    )

    # LOG stacktraces for failed jobs
    if job_info.status == JobStatusCodes.FAILED:
        LOG.debug("Redis job %s error; %s", job.id, job.exc_info)
        if raise_on_exception:
            raise JobFailedError(job.exc_info or f"Job {job.id} failed with no exception info available.")
    return job_info
