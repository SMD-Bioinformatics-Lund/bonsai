""" Module for checking the integrity of signature files recorded in the database. """

import datetime as dt
import logging

from minhash_service import __version__ as sourmash_version
from minhash_service.config import Settings
from minhash_service.infrastructure.signature_storage import SignatureStorage
from minhash_service.tasks import get_signature_repo
from minhash_service.minhash.io import (
    list_signatures_in_index,
    get_sbt_index,
)

from .report_model import IntegrityReport, InitiatorType

LOG = logging.getLogger(__name__)

def check_signature_integrity(initiator: InitiatorType, settings: Settings) -> IntegrityReport:
    """ Check that all signature files recorded in the database exist on disk."""
    start_time = dt.datetime.now(dt.timezone.utc)
    repo = get_signature_repo()
    store = SignatureStorage(
        base_dir=settings.signature_dir, trash_dir=settings.trash_dir
    )
    idx = get_sbt_index(cnf=settings, check=True)
    indexed_signatures: list[str] = [sig.name for sig in list_signatures_in_index(idx)]

    all_records = repo.get_all_signatures()
    n_signatures: int = 0
    missing_files: list[str] = []
    corrupted_files: list[str] = []
    should_be_indexed: list[str] = []
    should_not_be_indexed: list[str] = []
    for record in all_records:
        n_signatures += 1
        if not record.signature_path.exists():
            missing_files.append(record.sample_id)
            LOG.error("Signature file for sample_id %s is missing.", record.sample_id)
            continue
        if not store.check_file_integrity(record.signature_path, record.checksum):
            corrupted_files.append(record.sample_id)
            LOG.error(
                "Signature file for sample_id %s might be corrupted.",
                record.sample_id,
            )
        if record.has_been_indexed and record.sample_id not in indexed_signatures:
            LOG.error(
                "Signature file for sample_id %s is marked as indexed but not in index.",
                record.sample_id,
            )
            should_be_indexed.append(record.sample_id)
        elif not record.has_been_indexed and record.sample_id in indexed_signatures:
            LOG.error(
                "Signature file for sample_id %s is not marked as indexed but is still in the index.",
                record.sample_id,
            )
            should_not_be_indexed.append(record.sample_id)
    return IntegrityReport(
        timestamp=dt.datetime.now(dt.timezone.utc),
        initiated_by=initiator,
        duration=(dt.datetime.now(dt.timezone.utc) - start_time).seconds,
        version=sourmash_version,
        total_records=n_signatures,
        total_indexed=len(indexed_signatures),
        missing_files=missing_files,
        corrupted_files=corrupted_files,
        should_be_indexed=should_be_indexed,
        should_not_be_indexed=should_not_be_indexed,
    )