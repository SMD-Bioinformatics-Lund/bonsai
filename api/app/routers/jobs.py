"""Routes for interacting with submitted jobs."""
from ..redis import check_redis_job_status, JobStatus
from fastapi import APIRouter, status
import logging

LOG = logging.getLogger(__name__)

DEFAULT_TAGS = [
    "jobs",
]
READ_PERMISSION = "job:read"
WRITE_PERMISSION = "job:write"

router = APIRouter()

@router.get("/job/status/{job_id}", status_code=status.HTTP_200_OK, tags=DEFAULT_TAGS)
async def check_job_status(job_id: str) -> JobStatus:
    """Entrypoint for checking status of running jobs."""
    info = check_redis_job_status(job_id=job_id)
    return info