"""Functions relating to scheduling allele clustering jobs."""

import logging
from bonsai_api.crud.cluster import TypingProfileOutput, get_unplaced_samples
from bonsai_api.exceptions import InvalidDataFormat

import pandas as pd

from . import ClusterMethod, SubmittedJob
from .queue import redis

LOG = logging.getLogger(__name__)


def schedule_cluster_samples(
    profiles: TypingProfileOutput, cluster_method: ClusterMethod
) -> SubmittedJob:
    """Schedule clustering on the provided allele profile.

    :return: Information of submitted job
    :rtype: SubmittedJob
    """
    task = "allele_cluster_service.tasks.cluster"
    # convert the allele profile object to two arrays, one with names and another with
    # a tsv representation of the profile
    unplaced = get_unplaced_samples(profiles)
    unplaced_ids = {sample.sample_id for sample in unplaced}
    placed = [profile for profile in profiles if profile.sample_id not in unplaced_ids]
    if not placed:
        raise InvalidDataFormat("No selected sample has usable allele calls.")
    sample_ids = []
    allele_profile = []
    for profile in placed:
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
        method=cluster_method.value,
        sample_ids=sample_ids,
        meta={"unplaced_samples": [sample.model_dump() for sample in unplaced]},
        job_timeout="30m",
    )
    LOG.debug("Submitting job, %s to %s", task, job.worker_name)
    return SubmittedJob(id=job.id, task=task)
