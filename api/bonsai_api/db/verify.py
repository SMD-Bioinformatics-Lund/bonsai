"""Verify database content and integrity"""

import asyncio
import logging
from asyncio import TimeoutError
from pathlib import Path

from pydantic import BaseModel

from ..config import settings
from ..io import is_file_readable
from ..models.sample import SampleInDatabase
from ..redis import minhash, ska
from ..redis.queue import JobFailedError
from ..redis.utils import SubmittedJob, wait_for_job

LOG = logging.getLogger(__name__)


class MissingFile(BaseModel):
    """Information on missing file."""

    sample_id: str
    file_type: str
    error_type: str
    path: Path


MISSING_FILES = list[MissingFile]


def verify_reference_genome(sample: SampleInDatabase) -> MISSING_FILES:
    """Verify paths to the reference genome and assets."""
    missing_files: MISSING_FILES = []

    base_path = Path(settings.reference_genomes_dir)
    if sample.reference_genome is not None:
        ref_files: dict[str, str] = {
            "fa": sample.reference_genome.fasta,
            "fai": sample.reference_genome.fasta_index,
            "gff": sample.reference_genome.genes,
        }
        for ftype, fname in ref_files.items():
            file_path = base_path.joinpath(fname)
            try:
                is_file_readable(str(file_path))
            except (FileNotFoundError, PermissionError) as err:
                missing_files.append(
                    MissingFile(
                        sample_id=sample.sample_id,
                        file_type=f"ref_genome_{ftype}",
                        error_type=type(err).__name__,
                        path=file_path,
                    )
                )
    return missing_files


def verify_read_mapping(sample: SampleInDatabase) -> MissingFile | None:
    """Check paths for mapped reads."""
    if sample.read_mapping is not None:
        try:
            is_file_readable(sample.read_mapping)
        except (FileNotFoundError, PermissionError) as err:
            return MissingFile(
                sample_id=sample.sample_id,
                file_type="read_mapping",
                error_type=type(err).__name__,
                path=Path(sample.read_mapping),
            )


def verify_ska_index(sample: SampleInDatabase, timeout: int = 60) -> MissingFile | None:
    """Verify files for SKA clustering."""
    if sample.ska_index is None:
        return None

    job: SubmittedJob = ska.schedule_check_index(sample.ska_index)
    loop = asyncio.get_event_loop()
    async_func = wait_for_job(job, timeout=timeout)
    job_status = loop.run_until_complete(async_func)
    if job_status.result is None:
        return MissingFile(
            sample_id=sample.sample_id,
            file_type="ska_index",
            error_type="FileNotFound",
            path=Path(sample.ska_index),
        )


def verify_sourmash_files(
    sample: SampleInDatabase, timeout: int = 60
) -> MissingFile | None:
    """Verify files for minhash clustering."""
    if sample.genome_signature is not None:
        job: SubmittedJob = minhash.schedule_check_signature(sample.sample_id)
        try:
            loop = asyncio.get_event_loop()
            async_func = wait_for_job(job, timeout=timeout)
            job_status = loop.run_until_complete(async_func)
        except JobFailedError as err:
            LOG.info(
                "Something went wrong when checking minhash sequence of %s, skipping...",
                sample.sample_id,
            )
            LOG.debug("Minhash error: %s", err)
        except TimeoutError as err:
            LOG.debug("Job to verify sample '%s' timed out", sample.sample_id)
        else:
            # report if file was missing
            if job_status.result is None:
                return MissingFile(
                    sample_id=sample.sample_id,
                    file_type="minhash_index",
                    error_type="FileNotFound",
                    path=Path(sample.genome_signature),
                )
