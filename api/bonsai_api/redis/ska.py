"""Operations on minhash signatures."""
import logging
from typing import List

from rq import Retry
from rq.job import Dependency

from . import ClusterMethod, SubmittedJob, TypingMethod
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