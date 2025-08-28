"""Routes for interacting with submitted jobs."""

import logging

from fastapi import APIRouter, status

from bonsai_api.redis.queue import JobStatus, check_redis_job_status
from bonsai_api.redis import minhash
from bonsai_api.redis.models import SubmittedJob
from .shared import RouterTags

LOG = logging.getLogger(__name__)

READ_PERMISSION = "job:read"
WRITE_PERMISSION = "job:write"

router = APIRouter()


@router.get("/job/status/{job_id}", status_code=status.HTTP_200_OK, tags=[RouterTags.JOB])
async def check_job_status(job_id: str) -> JobStatus:
    """Entrypoint for checking status of running jobs.

    :param job_id: Redis job id
    :type job_id: str
    :return: Job information.
    :rtype: JobStatus
    """
    info = check_redis_job_status(job_id=job_id)
    return info


@router.get("/job/minhash/integrity-report", status_code=status.HTTP_200_OK, tags=[RouterTags.JOB, "minhash"])
async def get_report_from_minhash() -> SubmittedJob:
    """Get latest integrity report the minhash service.

    :rtype: JobStatus
    """
    return minhash.schedule_get_latest_report()
