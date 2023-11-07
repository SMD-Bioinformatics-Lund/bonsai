"""Operations on minhash signatures."""
import logging
from typing import List
from .queue import redis
from rq import Retry
from rq.job import Dependency
from . import SubmittedJob, ClusterMethod, TypingMethod


LOG = logging.getLogger(__name__)


def schedule_add_genome_signature(sample_id: str, signature) -> SubmittedJob | str:
    """Schedule adding signature to index."""
    TASK = "app.tasks.add_signature"
    job = redis.minhash.enqueue(TASK, sample_id=sample_id, signature=signature, job_timeout='30m')
    LOG.debug(f"Submitting job, {TASK} to {job.worker_name}")
    return SubmittedJob(id=job.id, task=TASK)


def schedule_add_genome_signature_to_index(sample_ids: List[str], depends_on: List[str] = None, **enqueue_kwargs) -> SubmittedJob:
    """
    Schedule adding signature to index.

    The job can depend on the completion of previous jobs by providing a job_id
    """
    TASK = "app.tasks.index"
    submit_kwargs = {"retry": Retry(max=3, interval=60), **enqueue_kwargs}  # default retry 3 times, 60 in between
    # make job depend on the job of others
    if depends_on is not None:
        submit_kwargs['depends_on'] = Dependency(
            jobs=depends_on, 
            allow_failure=False,    # allow if dependent job fails
            enqueue_at_front=True  # put dependents at front of queue
        )

    # submit job
    job = redis.minhash.enqueue(TASK, sample_ids=sample_ids, job_timeout='30m', **submit_kwargs)
    LOG.debug(f"Submitting job, {TASK} to {job.worker_name}")
    return SubmittedJob(id=job.id, task=TASK)


def schedule_find_similar_samples(
    sample_id: str, min_similarity: float, limit: int | None = None
) -> SubmittedJob:
    """Schedule find similar samples job.

    min_similarity - minimum similarity score to be included
    """
    TASK = "app.tasks.similar"
    job = redis.minhash.enqueue(TASK, sample_id=sample_id, 
                                min_similarity=min_similarity, limit=limit, 
                                job_timeout='30m')
    LOG.debug(f"Submitting job, {TASK} to {job.worker_name}")
    return SubmittedJob(id=job.id, task=TASK)


def schedule_cluster_samples(sample_ids: List[str], cluster_method: ClusterMethod) -> SubmittedJob:
    """Schedule find similar samples job.

    min_similarity - minimum similarity score to be included
    """
    TASK = "app.tasks.cluster"
    job = redis.minhash.enqueue(TASK, sample_ids=sample_ids, cluster_method=cluster_method.value, job_timeout='30m') 
    LOG.debug(f"Submitting job, {TASK} to {job.worker_name}; {job}")
    return SubmittedJob(id=job.id, task=TASK)


def schedule_find_similar_and_cluster(
    sample_id: str, min_similarity: float, typing_method: TypingMethod, 
    cluster_method: ClusterMethod, limit: int | None = None
) -> SubmittedJob:
    """Schedule a job to find similar samples and cluster the results

    min_similarity - minimum similarity score to be included
    typing_method - what data the samples should be clustered on
    linkage - the linkage function to use when clustering
    """
    if typing_method == TypingMethod.MINHASH:
        TASK = "app.tasks.find_similar_and_cluster"
        job = redis.minhash.enqueue(TASK, sample_id=sample_id, 
                                    min_similarity=min_similarity, limit=limit, 
                                    cluster_method=cluster_method.value, job_timeout='30m')
        LOG.debug(f"Submitting job, {TASK} to {job.worker_name}")
    else:
        raise ValueError(f"{typing_method} is not implemented yet")
    return SubmittedJob(id=job.id, task=TASK)