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
    """Schedule clustering on the provided allele profile.

    :return: Information of submitted job
    :rtype: SubmittedJob
    """
    task = "allele_cluster_service.tasks.cluster"
    # convert the allele profile object to two arrays, one with names and another with
    # a tsv representation of the profile
    sample_ids = []
    allele_profile = []
    for profile in profiles:
        sample_ids.append(profile.sample_id)
        allele_profile.append(profile.allele_profile())
    # Prefix locus names so MStree does not mistake ST or # loci for metadata.
    allele_profile = [
        {f"allele:{gene}": call for gene, call in profile.items()}
        for profile in allele_profile
    ]
    # Keep the sample ID column explicit in the API/worker TSV contract.
    profile_tsv = (
        pd.DataFrame(allele_profile, index=sample_ids)
        .dropna(axis=1, how="all")  # remove cols with all nulls
        .fillna("-")  # replace nulls with MStree null char, "-"
        .to_csv(sep="\t", index_label="sample_id")
    )
    job = redis.allele.enqueue(
        task, profile=profile_tsv, method=cluster_method.value, job_timeout="30m"
    )
    LOG.debug("Submitting job, %s to %s", task, job.worker_name)
    return SubmittedJob(id=job.id, task=task)
