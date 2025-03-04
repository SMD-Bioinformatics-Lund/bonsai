"""Functions for handling redis jobs."""

import asyncio
import logging

from .models import SubmittedJob
from .queue import JobStatus, JobStatusCodes, check_redis_job_status

LOG = logging.getLogger(__name__)


async def wait_until_complete(job: SubmittedJob, delay: int) -> JobStatus:
    """Async wrapper for check_redis_job_status"""
    job_status = check_redis_job_status(job.id)
    while job_status.status != JobStatusCodes.FINISHED:
        await asyncio.sleep(delay)
        job_status = check_redis_job_status(job.id, raise_on_exception=True)
    return job_status


async def wait_for_job(
    job: SubmittedJob, timeout: int = 60, delay: int = 1
) -> JobStatus | None:
    """Wait for redis job to complete."""
    try:
        job_status = await asyncio.wait_for(
            wait_until_complete(job, delay=delay), timeout=timeout
        )
    except asyncio.TimeoutError as error:
        LOG.warning(
            (
                "The job %s exceeded the timedout and "
                "could not be completed. Try increase "
                "the timeout."
            ),
            job.id,
        )
        raise error
    return job_status
