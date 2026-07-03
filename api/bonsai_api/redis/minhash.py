"""Operations for scheduling minhash jobs."""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any, Iterable

from rq import Retry

from bonsai_libs.jobs import schedule_job
from bonsai_api.models.enums import TypingMethod

from .models import ClusterMethod, SubmittedJob
from .queue import redis

LOG = logging.getLogger(__name__)

DEFAULT_JOB_TIMEOUT = "30m"
DEFAULT_RETRY = Retry(max=3, interval=60)

# RQ entrypoint executed by the worker
ENTRYPOINT = "minhash_service.tasks.execute_service_task"


class TaskName(StrEnum):
    """Valid registered task names for the minhash service."""

    ADD_SIGNATURE = "add_signature"
    REMOVE_SIGNATURE = "remove_signature"
    ADD_INDEX = "add_to_index"
    REMOVE_INDEX = "remove_from_index"
    EXCLUDE_SAMPLE = "exclude_from_analysis"
    INCLUDE_SAMPLE = "include_in_analysis"
    SEARCH_SIMILAR = "search_similar"
    CLUSTER_SAMPLES = "cluster_samples"
    CHECK_SIGNATURE = "check_signature"
    SIMILAR_N_CLUSTER = "find_similar_and_cluster"
    GET_REPORT = "get_integrity_report"


def enqueue_minhash_job(
    *,
    task: str,
    payload: dict[str, Any] | None = None,
    job_timeout: str | int | None = DEFAULT_JOB_TIMEOUT,
    retry: Retry | None = None,
    depends_on: Iterable[str] | None = None,
    metadata: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    **enqueue_kwargs: Any,
):
    return schedule_job(
        queue=redis.minhash,
        entrypoint=ENTRYPOINT,
        task=task,
        payload=payload,
        context=context,
        metadata=metadata,
        job_timeout=job_timeout,
        retry=retry,
        depends_on=depends_on,
        **enqueue_kwargs,
    )


def schedule_add_genome_signature(sample_id: str, signature_json: str) -> SubmittedJob:
    """Schedule adding a genome signature."""
    task = TaskName.ADD_SIGNATURE
    job = enqueue_minhash_job(
        queue=redis.minhash,
        task=str(task),
        retry=None,
        payload={
            "sample_id": sample_id,
            "signature": signature_json,
        },
    )
    return SubmittedJob(id=job.id, task=str(task))


def schedule_remove_genome_signature(sample_id: str) -> SubmittedJob:
    """Schedule removing a genome signature."""
    task = TaskName.REMOVE_SIGNATURE
    job = enqueue_minhash_job(
        queue=redis.minhash,
        task=str(task),
        retry=None,
        payload={"sample_id": sample_id},
    )
    return SubmittedJob(id=job.id, task=str(task))


def schedule_add_genome_signature_to_index(
    sample_ids: list[str],
    depends_on: list[str] | None = None,
    **enqueue_kwargs: Any,
) -> SubmittedJob:
    """Schedule adding signatures to the index."""
    task = TaskName.ADD_INDEX
    job = enqueue_minhash_job(
        queue=redis.minhash,
        task=str(task),
        depends_on=depends_on,
        retry=DEFAULT_RETRY,
        payload={"sample_ids": sample_ids},
        **enqueue_kwargs,
    )
    return SubmittedJob(id=job.id, task=str(task))


def schedule_remove_genome_signature_from_index(
    sample_ids: list[str],
    depends_on: list[str] | None = None,
    **enqueue_kwargs: Any,
) -> SubmittedJob:
    """Schedule removing signatures from the index."""
    task = TaskName.REMOVE_INDEX
    job = enqueue_minhash_job(
        queue=redis.minhash,
        task=str(task),
        depends_on=depends_on,
        retry=DEFAULT_RETRY,
        payload={"sample_ids": sample_ids},
        **enqueue_kwargs,
    )
    return SubmittedJob(id=job.id, task=str(task))


def schedule_find_similar_samples(
    sample_id: str,
    min_similarity: float,
    limit: int | None = None,
    narrow_to_sample_ids: list[str] | None = None,
) -> SubmittedJob:
    """Schedule a job to find similar samples."""
    task = TaskName.SEARCH_SIMILAR
    job = enqueue_minhash_job(
        queue=redis.minhash,
        task=str(task),
        retry=None,
        payload={
            "sample_id": sample_id,
            "min_similarity": min_similarity,
            "limit": limit,
            "subset_sample_ids": narrow_to_sample_ids,
        },
    )
    return SubmittedJob(id=job.id, task=str(task))


def schedule_cluster_samples(
    sample_ids: list[str],
    cluster_method: ClusterMethod,
) -> SubmittedJob:
    """Schedule clustering of the given samples."""
    task = TaskName.CLUSTER_SAMPLES
    job = enqueue_minhash_job(
        queue=redis.minhash,
        task=str(task),
        retry=None,
        payload={
            "sample_ids": sample_ids,
            "cluster_method": cluster_method.value,
        },
    )
    return SubmittedJob(id=job.id, task=str(task))


def schedule_find_similar_and_cluster(
    sample_id: str,
    min_similarity: float,
    typing_method: TypingMethod,
    cluster_method: ClusterMethod,
    limit: int | None = None,
    narrow_to_sample_ids: list[str] | None = None,
) -> SubmittedJob:
    """
    Schedule a job to find similar samples and cluster the results.

    Parameters
    ----------
    sample_id:
        Reference sample ID.
    min_similarity:
        Minimum similarity score to include in the result.
    typing_method:
        Typing method requested by the caller.
    cluster_method:
        Clustering strategy for the final result.
    limit:
        Optional maximum number of similar samples.
    narrow_to_sample_ids:
        Optional subset restriction.
    """
    if typing_method != TypingMethod.MINHASH:
        raise NotImplementedError(f"{typing_method} is not implemented yet")

    task = TaskName.SIMILAR_N_CLUSTER
    job = enqueue_minhash_job(
        queue=redis.minhash,
        task=str(task),
        retry=None,
        payload={
            "sample_id": sample_id,
            "min_similarity": min_similarity,
            "limit": limit,
            "subset_sample_ids": narrow_to_sample_ids,
            "cluster_method": cluster_method.value,
        },
    )
    return SubmittedJob(id=job.id, task=str(task))


def schedule_check_signature(sample_id: str) -> SubmittedJob:
    """Schedule a task to check whether a signature exists for the sample."""
    task = TaskName.CHECK_SIGNATURE
    job = enqueue_minhash_job(
        queue=redis.minhash,
        task=str(task),
        retry=None,
        payload={"sample_id": sample_id},
    )
    return SubmittedJob(id=job.id, task=str(task))


def schedule_get_latest_report() -> SubmittedJob:
    """Schedule retrieval of the latest integrity report."""
    task = TaskName.GET_REPORT
    job = enqueue_minhash_job(
        queue=redis.minhash,
        task=str(task),
        retry=None,
        payload={},
    )
    return SubmittedJob(id=job.id, task=str(task))


def exclude_from_analysis(sample_id: str) -> SubmittedJob:
    """Schedule exclusion of a sample from analysis."""
    task = TaskName.EXCLUDE_SAMPLE
    job = enqueue_minhash_job(
        queue=redis.minhash,
        task=str(task),
        retry=None,
        payload={"sample_ids": [sample_id]},
    )
    return SubmittedJob(id=job.id, task=str(task))


def include_in_analysis(sample_id: str) -> SubmittedJob:
    """Schedule inclusion of a sample in analysis."""
    task = TaskName.INCLUDE_SAMPLE
    job = enqueue_minhash_job(
        queue=redis.minhash,
        task=str(task),
        retry=None,
        payload={"sample_ids": [sample_id]},
    )
    return SubmittedJob(id=job.id, task=str(task))