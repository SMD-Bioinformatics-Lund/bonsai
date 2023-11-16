"""Functions relating to scheduling allele clustering jobs."""
import logging
from typing import List

import pandas as pd

from . import ClusterMethod, SubmittedJob
from .queue import redis

LOG = logging.getLogger(__name__)


def schedule_cluster_samples(
    profiles: List[str], cluster_method: ClusterMethod
) -> SubmittedJob:
    """Schedule clustering on the provided allele profile."""
    TASK = "allele_cluster_service.tasks.cluster"
    # convert the allele profile object to two arrays, one with names and another with
    # a tsv representation of the profile
    sample_ids = []
    allele_profile = []
    for profile in profiles:
        sample_ids.append(profile.sample_id)
        allele_profile.append(profile.allele_profile())
    # convert to pandas dataframe
    profile_tsv = pd.DataFrame(allele_profile, dtype="UInt64").to_csv(sep="\t")
    job = redis.allele.enqueue(
        TASK, profile=profile_tsv, method=cluster_method.value, job_timeout="30m"
    )
    LOG.debug(f"Submitting job, {TASK} to {job.worker_name}; {job}")
    return SubmittedJob(id=job.id, task=TASK)
