"""Functions relating to scheduling allele clustering jobs."""

import logging

import pandas as pd

from bonsai_api.models.enums import ClusterStrategy

from . import SubmittedJob
from .queue import redis

LOG = logging.getLogger(__name__)

VALID_ALGORITHMS = [
    ClusterStrategy.MSTREE_V1,
    ClusterStrategy.MSTREE_V2,
    ClusterStrategy.NJ,
    ClusterStrategy.RAPID_NJ,
    ClusterStrategy.NINJA,
]

def _validate_strategy(strategy: ClusterStrategy) -> None:
    """Validate the selected stategy is valid for allele clustering."""
    if strategy not in VALID_ALGORITHMS:
        raise ValueError(f"Strategy: {strategy} is not supported by the allele cluster service.")


def schedule_cluster_samples(
    profiles: list[str], cluster_method: ClusterStrategy
) -> SubmittedJob:
    """Schedule clustering on the provided allele profile."""
    _validate_strategy(cluster_method)

    task = "allele_cluster_service.tasks.cluster"

    # convert the allele profile object to two arrays, one with names and another with
    # a tsv representation of the profile
    sample_ids = []
    allele_profile = []
    for profile in profiles:
        sample_ids.append(profile.sample_id)
        allele_profile.append(profile.allele_profile())
    # convert to pandas dataframe
    profile_tsv = (
        pd.DataFrame(allele_profile, index=sample_ids)
        .dropna(axis=1, how="all")  # remove cols with all nulls
        .fillna("-")  # replace nulls with MStree null char, "-"
        .to_csv(sep="\t")  # convert to tsv string
    )

    job = redis.allele.enqueue(
        task,
        profile=profile_tsv,
        method=str(cluster_method),
        job_timeout="30m"
    )
    LOG.debug("Submitting job, %s to %s", task, job.worker_name)
    return SubmittedJob(id=job.id, task=task)
