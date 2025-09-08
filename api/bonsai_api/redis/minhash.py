"""Operations on minhash signatures."""

import logging
from enum import StrEnum
from typing import Any, Iterable

from rq import Queue, Retry
from rq.job import Dependency

from ..models.cluster import TypingMethod
from .models import ClusterMethod, SubmittedJob
from .queue import redis

LOG = logging.getLogger(__name__)

DEFAULT_JOB_TIMEOUT = "30m"
DEFAULT_RETRY = Retry(max=3, interval=60)  # shared default for retry-able jobs
DISPATCH = "minhash_service.tasks.dispatch_job"


class TaskName(StrEnum):
    """Valid names for minhash tasks."""

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


def enqueue_job(
    *,
    queue: Queue,
    dispatch: str,
    task: str,
    job_timeout: str | int | None = DEFAULT_JOB_TIMEOUT,
    depends_on: Iterable[str] | None = None,
    retry: Retry | None = None,
    **kwargs: Any,
):
    """Shared helper to enqueue RQ jobs with consistent defaults.


    Parameters
    ----------
    queue : rq.Queue
        The RQ queue to enqueue to (e.g., `redis.minhash`).
    dispatch : str
        Fully qualified function path that workers import (e.g., "pkg.tasks.dispatch").
    task : str
        Task identifier to route inside the dispatch function.
    job_timeout : str | int | None
        RQ job timeout; string (e.g., "30m") or seconds. Defaults to 30 minutes.
    depends_on : Iterable[str] | None
        Job IDs this job depends on. Creates a Dependency with allow_failure=False.
    retry : Retry | None
        RQ Retry policy; pass None to disable retries.
    log : logging.Logger | None
        Optional logger for debug messages.
    **kwargs :
        Extra kwargs passed as job kwargs to the dispatch function.

    Returns
    -------
    rq.job.Job
        The enqueued RQ job.
    """
    submit_kwargs: dict[str, str | int | Retry | Dependency] = {}
    if job_timeout is not None:
        submit_kwargs["job_timeout"] = job_timeout

    if retry is not None:
        submit_kwargs["retry"] = retry

    if depends_on:
        submit_kwargs["depends_on"] = Dependency(
            jobs=list(depends_on), allow_failure=False, enqueue_at_front=True
        )
    job = queue.enqueue(dispatch, task=task, **kwargs, **submit_kwargs)
    LOG.debug("Submitting job, %s to %s", task, getattr(job, "worker_name", None))
    return job


def schedule_add_genome_signature(sample_id: str, signature_json: str) -> SubmittedJob:
    """Schedule adding a genome signature (no retries by default)."""
    task = str(TaskName.ADD_SIGNATURE)
    job = enqueue_job(
        queue=redis.minhash,
        dispatch=DISPATCH,
        task=task,
        retry=None,  # keep behavior identical (no retry in original)
        sample_id=sample_id,
        signature=signature_json,
    )
    return SubmittedJob(id=job.id, task=task)


def schedule_remove_genome_signature(sample_id: str) -> SubmittedJob:
    """Schedule removing a genome signature (no retries by default)."""
    task = str(TaskName.REMOVE_SIGNATURE)
    job = enqueue_job(
        queue=redis.minhash,
        dispatch=DISPATCH,
        task=task,
        retry=None,  # keep behavior identical (no retry in original)
        sample_id=sample_id,
    )
    return SubmittedJob(id=job.id, task=task)


def schedule_add_genome_signature_to_index(
    sample_ids: list[str],
    depends_on: list[str] | None = None,
    **enqueue_kwargs: Any,
) -> SubmittedJob:
    """
    Schedule adding signatures to index.

    The job can depend on the completion of previous jobs by providing job IDs via `depends_on`.
    Retries are enabled by default (3x, 60s).
    """
    task = str(TaskName.ADD_INDEX)
    job = enqueue_job(
        queue=redis.minhash,
        dispatch=DISPATCH,
        task=task,
        depends_on=depends_on,
        retry=DEFAULT_RETRY,
        sample_ids=sample_ids,
        **enqueue_kwargs,
    )
    return SubmittedJob(id=job.id, task=task)


def schedule_remove_genome_signature_from_index(
    sample_ids: list[str],
    depends_on: list[str] | None = None,
    **enqueue_kwargs: Any,
) -> SubmittedJob:
    """
    Schedule removing signatures from index.

    The job can depend on the completion of previous jobs by providing job IDs via `depends_on`.
    Retries are enabled by default (3x, 60s).
    """
    task = str(TaskName.REMOVE_INDEX)
    job = enqueue_job(
        queue=redis.minhash,
        dispatch=DISPATCH,
        task=task,
        depends_on=depends_on,
        retry=DEFAULT_RETRY,
        sample_ids=sample_ids,
        **enqueue_kwargs,
    )
    return SubmittedJob(id=job.id, task=task)


def schedule_find_similar_samples(
    sample_id: str,
    min_similarity: float,
    limit: int | None = None,
    narrow_to_sample_ids: list[str] | None = None,
) -> SubmittedJob:
    """Schedule a job to find similar samples (no retries by default)."""
    task = str(TaskName.SEARCH_SIMILAR)
    job = enqueue_job(
        queue=redis.minhash,
        dispatch=DISPATCH,
        task=task,
        retry=None,
        sample_id=sample_id,
        min_similarity=min_similarity,
        limit=limit,
        subset_sample_ids=narrow_to_sample_ids,
    )
    return SubmittedJob(id=job.id, task=task)


def schedule_cluster_samples(
    sample_ids: list[str],
    cluster_method: ClusterMethod,
) -> SubmittedJob:
    """Schedule a job to cluster the given samples (no retries by default)."""
    task = str(TaskName.CLUSTER_SAMPLES)
    job = enqueue_job(
        queue=redis.minhash,
        dispatch=DISPATCH,
        task=task,
        retry=None,
        sample_ids=sample_ids,
        cluster_method=cluster_method.value,
    )
    return SubmittedJob(id=job.id, task=task)


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

    min_similarity - minimum similarity score to be included
    typing_method - what data the samples should be clustered on
    """
    if typing_method != TypingMethod.MINHASH:
        raise NotImplementedError(f"{typing_method} is not implemented yet")

    task = str(TaskName.SIMILAR_N_CLUSTER)
    job = enqueue_job(
        queue=redis.minhash,
        dispatch=DISPATCH,  # <-- fixed missing comma from original
        task=task,
        retry=None,
        sample_id=sample_id,
        min_similarity=min_similarity,
        limit=limit,
        subset_sample_ids=narrow_to_sample_ids,
        cluster_method=cluster_method.value,
    )
    return SubmittedJob(id=job.id, task=task)


def schedule_check_signature(sample_id: str) -> SubmittedJob:
    """Schedule a task to check if a signature exists for the sample."""
    task = str(TaskName.CHECK_SIGNATURE)
    job = enqueue_job(
        queue=redis.minhash,
        dispatch=DISPATCH,
        task=task,
        retry=None,
        sample_id=sample_id,
    )
    return SubmittedJob(id=job.id, task=task)


def schedule_get_latest_report() -> SubmittedJob:
    """Schedule a task to get the latest integrity report."""
    task = str(TaskName.GET_REPORT)
    job = enqueue_job(
        queue=redis.minhash,
        dispatch=DISPATCH,
        task=task,
        retry=None,
    )
    return SubmittedJob(id=job.id, task=task)


def exclude_from_analysis(sample_id: str) -> SubmittedJob:
    """Update wether a sample should be excluded."""
    task = str(TaskName.EXCLUDE_SAMPLE)
    job = enqueue_job(
        queue=redis.minhash,
        dispatch=DISPATCH,
        task=task,
        retry=None,
        sample_ids=[sample_id],
    )
    return SubmittedJob(id=job.id, task=task)


def include_in_analysis(sample_id: str) -> SubmittedJob:
    """Update wether a sample should be excluded."""
    task = str(TaskName.INCLUDE_SAMPLE)
    job = enqueue_job(
        queue=redis.minhash,
        dispatch=DISPATCH,
        task=task,
        retry=None,
        sample_ids=[sample_id],
    )
    return SubmittedJob(id=job.id, task=task)
