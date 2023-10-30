"""Operations on minhash signatures."""
import logging
from typing import List
from app.redis import redis
from rq import Retry
from rq.job import Dependency
from ..models.base import RWModel

LOG = logging.getLogger(__name__)

class SubmittedJob(RWModel):
    """Container for submitted jobs."""

    id: str
    task: str


def schedule_add_genome_signature(sample_id: str, signature) -> SubmittedJob | str:
    """Schedule adding signature to index."""
    TASK = "app.tasks.add_signature"
    job = redis.minhash.enqueue(TASK, sample_id=sample_id, signature=signature, job_timeout='30m')
    LOG.debug(f"Submitting job, {TASK} to {job.worker_name}")
    return SubmittedJob(id=job.id, task=TASK)


def schedule_add_genome_signature_to_index(sample_ids: List[str], depends_on: List[str] = None) -> SubmittedJob:
    """
    Schedule adding signature to index.

    The job can depend on the completion of previous jobs by providing a job_id
    """
    TASK = "app.tasks.index"
    submit_kwargs = {retry: Retry(max=3, interval=60)}  # default retry 3 times, 60 in between
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


def schedule_get_samples_similar_to_reference(
    sample_id: str, min_similarity: float, limit: int | None = None
) -> SubmittedJob:
    """Schedule find similar samples job.

    min_similarity - minimum similarity score to be included
    """
    TASK = "app.tasks.similar"
    job = redis.minhash.enqueue(TASK, sample_id=sample_id, 
                                min_similarity=min_similarity, job_timeout='30m')
    LOG.debug(f"Submitting job, {TASK} to {job.worker_name}")
    return SubmittedJob(id=job.id, task=TASK)