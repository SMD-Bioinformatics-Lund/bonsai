"""Operations on minhash signatures."""

import logging

from bonsai_libs.clustering import ClusteringAlgorithm

from bonsai_api.models.enums import ClusterStrategy

from .utils import _parse_linkage_method
from .models import SubmittedJob
from .queue import redis

LOG = logging.getLogger(__name__)


def schedule_cluster_samples(
    index_files: dict[str, str], cluster_method: ClusterStrategy
) -> SubmittedJob:
    """Schedule SNV clustering uisng SKA."""
    task = "ska_service.tasks.cluster"
    LOG.debug("Schedule SKA clustering of %s with %s", index_files, cluster_method)

    if ClusterStrategy == ClusterStrategy.MST:
        algorithm = ClusteringAlgorithm.MST
        method = None
    else:
        algorithm = ClusteringAlgorithm.HIERARCHICAL
        method = str(_parse_linkage_method(str(cluster_method)))

    job = redis.ska.enqueue(
        task,
        indexes=index_files,
        algorithm=algorithm,
        cluster_method=method,
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
