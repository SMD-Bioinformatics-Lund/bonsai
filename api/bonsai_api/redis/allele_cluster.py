"""Functions relating to scheduling allele clustering jobs."""

import logging
import csv
import io

from bonsai_api.crud.cluster import TypingProfileOutput, get_unplaced_samples

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
    unplaced = get_unplaced_samples(profiles)
    unplaced_ids = {sample.sample_id for sample in unplaced}
    placed = [profile for profile in profiles if profile.sample_id not in unplaced_ids]
    if not placed:
        raise ValueError("No selected sample has usable allele calls")
    sample_ids = [profile.sample_id for profile in placed]
    allele_profiles = [profile.allele_profile() for profile in placed]
    loci = sorted(
        {
            gene
            for profile in allele_profiles
            for gene, call in profile.items()
            if call is not None
        }
    )
    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")
    # A named index column prevents a leading tab from shifting the worker's header.
    # Distinguish real loci from reserved metadata labels in the generic reader.
    writer.writerow(["sample_id", *(f"allele:{gene}" for gene in loci)])
    for sample_id, profile in zip(sample_ids, allele_profiles):
        writer.writerow(
            [
                sample_id,
                *(
                    profile.get(gene) if profile.get(gene) is not None else "-"
                    for gene in loci
                ),
            ]
        )
    profile_tsv = output.getvalue()
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
