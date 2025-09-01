"""Operations on minhash signatures."""

import logging
from typing import List

from .models import ClusterMethod, SubmittedJob
from .queue import redis

LOG = logging.getLogger(__name__)


def schedule_cluster_samples(
    index_files: List[str], cluster_method: ClusterMethod
) -> SubmittedJob:
    """Schedule SNV clustering uisng SKA."""
    task = "ska_service.tasks.cluster"
    LOG.debug("Schedule SKA clustering of %s with %s", index_files, cluster_method)
    job = redis.ska.enqueue(
        task,
        indexes=index_files,
        cluster_method=cluster_method.value,
        job_timeout="30m",
    )
    LOG.debug("Submitting job, %s to %s", task, job.worker_name)
    return SubmittedJob(id=job.id, task=task)


def schedule_check_index(index_file: str) -> SubmittedJob:
    """Request the SKA service to check if index file is present."""
    task = "ska_service.tasks.check_index"
    LOG.debug("Schedule SKA to check whether '%s' exists.", index_file)
    job = redis.ska.enqueue(
        task,
        file_name=index_file,
        job_timeout="30m",
    )
    LOG.debug("Submitting job, %s to %s", task, job.worker_name)
    return SubmittedJob(id=job.id, task=task)
