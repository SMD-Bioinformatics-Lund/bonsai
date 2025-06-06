"""Functions for managing redis connections."""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from bonsai_api.config import settings
from pydantic import BaseModel
from redis import Redis
from rq import Queue
from rq.job import Job

LOG = logging.getLogger(__name__)


class JobFailedError(BaseException):
    """Failed redis job."""


class RedisQueue:  # pylint: disable=too-few-public-methods
    """Worker queue interface."""

    def __init__(self):
        """Setup connection and define queues."""
        self.connection = Redis(settings.redis_host, settings.redis_port)
        self.minhash: Queue = Queue("minhash", connection=self.connection)
        self.ska: Queue = Queue("ska", connection=self.connection)
        self.allele: Queue = Queue("allele_cluster", connection=self.connection)


redis = RedisQueue()


class JobStatusCodes(str, Enum):
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
    result: Any
    error: str | None = None
    submitted_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


def check_redis_job_status(job_id: str, raise_on_exception: False = False) -> JobStatus:
    """Check status of a job."""
    job = Job.fetch(job_id, connection=redis.connection)
    job_info = JobStatus(
        status=job.get_status(refresh=True),
        queue=job.origin,
        task=job.func_name,
        result=job.return_value(),
        submitted_at=job.enqueued_at,
        started_at=job.started_at,
        finished_at=job.ended_at,
    )
    # LOG stacktraces for failed jobs
    if job_info.status == JobStatusCodes.FAILED:
        LOG.debug("Redis job %s error; %s", job.id, job.exc_info)
        if raise_on_exception:
            raise JobFailedError(job.exc_info)
    return job_info
