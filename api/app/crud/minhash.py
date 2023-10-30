"""Operations on minhash signatures."""
import logging
import gzip
import pathlib
import sourmash
from app import config
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


def add_genome_signature_file(sample_id: str, signature) -> pathlib.Path:
    """
    Add new genome signature file to host file system.

    and create or update existing index if required.
    """
    # get signature directory
    LOG.info(f'Adding signature file for {sample_id}')
    signature_db = pathlib.Path(config.GENOME_SIGNATURE_DIR)
    # make db if signature db is not present
    if not signature_db.exists():
        signature_db.mkdir(parents=True, exist_ok=True)

    # check that signature doesnt exist
    signature_file = signature_db.joinpath(f"{sample_id}.sig")
    if signature_file.is_file():
        raise FileExistsError("Signature file already exists")

    # check if compressed and decompress data
    LOG.info('Check if signature is compressed')
    if signature[:2] == b"\x1f\x8b":
        LOG.debug("Decompressing gziped file")
        signature = gzip.decompress(signature)

    # save signature to file
    LOG.info("Writing genome signatures to file")
    try:
        with open(signature_file, "w") as out:
            print(signature.decode("utf-8"), file=out)
    except PermissionError:
        msg = f"Dont have permission to write file to disk, {signature_file}"
        LOG.error(msg)
        raise PermissionError(msg)

    return signature_file


def remove_genome_signature_file(sample_id: str) -> bool:
    """Remove an existing signature file from disk."""

    # get signature directory
    signature_db = pathlib.Path(config.GENOME_SIGNATURE_DIR)

    # check that signature doesnt exist
    signature_file = signature_db.joinpath(f"{sample_id}.sig")
    if signature_file.is_file():
        # load signature to memory
        signature = next(
            sourmash.signature.load_signatures(
                signature_file, ksize=config.SIGNATURE_KMER_SIZE
            )
        )
        # remove file
        signature_file.unlink()
    else:
        raise FileNotFoundError(f"Signature file: {signature_file} not found")

    # remove signature to existing index
    sbt_filename = signature_db.joinpath("genomes.sbt.zip")
    if sbt_filename.is_file():
        LOG.debug("Append to existing file")
        tree = sourmash.load_file_as_index(str(sbt_filename))

        # add generated signature to bloom tree
        LOG.info("Adding genome signatures to index")
        leaf = sourmash.sbtmh.SigLeaf(signature.md5sum(), signature)
        tree.remove_many(leaf)

        try:
            tree.save(str(sbt_filename.resolve()))
        except PermissionError as err:
            LOG.error("Dont have permission to write file to disk")
            raise err
        return True
    LOG.info(f"Signature file: {signature_file} was removed")
    return False


def schedule_add_genome_signature(sample_id: str, signature, wait: bool = True) -> SubmittedJob | str:
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
    sample_id: str, min_similarity: float, kmer_size: int, limit: int | None = None
) -> SubmittedJob:
    """Schedule find similar samples job.

    min_similarity - minimum similarity score to be included
    """
    TASK = "app.tasks.similar"
    job = redis.minhash.enqueue(TASK, sample_id=sample_id, 
                                min_similarity=min_similarity, job_timeout='30m')
    LOG.debug(f"Submitting job, {TASK} to {job.worker_name}")
    return SubmittedJob(id=job.id, task=TASK)