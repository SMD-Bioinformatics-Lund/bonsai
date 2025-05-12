"""Routes for interacting with submitted jobs."""

import logging

from bonsai_api.redis.queue import JobStatus, check_redis_job_status
from .shared import RouterTags
from fastapi import APIRouter, status

LOG = logging.getLogger(__name__)

READ_PERMISSION = "job:read"
WRITE_PERMISSION = "job:write"

router = APIRouter()


@router.get(
    "/job/status/{job_id}", status_code=status.HTTP_200_OK, tags=[RouterTags.JOB]
)
async def check_job_status(job_id: str) -> JobStatus:
    """Entrypoint for checking status of running jobs.

    :param job_id: Redis job id
    :type job_id: str
    :return: Job information.
    :rtype: JobStatus
    """
    info = check_redis_job_status(job_id=job_id)
    return info
