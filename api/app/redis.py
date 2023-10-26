"""Functions for managing redis connections."""
from rq import Queue
from rq.job import Job
from redis import Redis
from pydantic import BaseModel
from app.config import REDIS_HOST, REDIS_PORT
from typing import Any
from datetime import datetime

class RedisQueue:
    """Worker queue interface."""

    def __init__(self):
        """Setup connection and define queues."""
        self.connection = Redis(REDIS_HOST, REDIS_PORT)
        self.minhash: Queue = Queue('minhash', connection=self.connection)
        self.cgmlst: Queue = Queue('cgmlst', connection=self.connection)


redis = RedisQueue()


class JobStatus(BaseModel):
    """Container for basic job information."""
    status: str
    queue: str
    result: Any
    submitted_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


def check_redis_job_status(job_id: str) -> JobStatus:
    """Check status of a job."""
    job = Job.fetch(job_id, connection=redis.connection)
    job_info = JobStatus(
        status=job.get_status(refresh=True),
        queue=job.origin,
        task=job.func_name,
        result=job.result,
        submitted_at=job.enqueued_at,
        started_at=job.started_at,
        finished_at=job.ended_at,
    )
    return job_info


def connect_to_redis():
    """Setup connection to redis message queue."""
    LOG.info("Initiate connection to Redis")
    redis.setup()  # initiate collections
    LOG.info("Connection successfull")