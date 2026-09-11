"""Routes for interacting with submitted jobs."""

import logging

from bonsai_api.redis import minhash
from bonsai_api.dependencies import get_current_active_user
from bonsai_api.models.user import UserOutputDatabase
from bonsai_api.redis.models import SubmittedJob
from bonsai_api.redis.queue import JobStatus, check_redis_job_status
from fastapi import APIRouter, Security, status

from .tags import RouterTags

LOG = logging.getLogger(__name__)

READ_PERMISSION = "samples:read"
WRITE_PERMISSION = "samples:write"

router = APIRouter(tags=[RouterTags.JOB])


@router.get(
    "/job/status/{job_id}", status_code=status.HTTP_200_OK
)
async def check_job_status(
    job_id: str,
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
) -> JobStatus:
    """Entrypoint for checking status of running jobs.

    :param job_id: Redis job id
    :type job_id: str
    :return: Job information.
    :rtype: JobStatus
    """
    info = check_redis_job_status(job_id=job_id)
    return info


@router.get(
    "/job/minhash/integrity-report",
    status_code=status.HTTP_202_ACCEPTED,
    tags=[RouterTags.JOB, "minhash"],
)
async def get_report_from_minhash(
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
) -> SubmittedJob:
    """Get latest integrity report the minhash service.

    :rtype: JobStatus
    """
    return minhash.schedule_get_latest_report()
