"""Define reddis tasks."""

import logging
from pathlib import Path
import datetime as dt

from . import __version__ as sourmash_version
from .audit import AuditTrailStore
from .config import settings
from .exceptions import FileRemovalError
from .infrastructure.signature_repository import SignatureRepository
from .infrastructure.signature_storage import SignatureStorage
from .minhash.cluster import ClusterMethod, cluster_signatures
from .minhash.io import (
    add_signatures_to_index,
    list_signatures_in_index,
    remove_signatures_from_index,
    write_signature,
    get_sbt_index,
)
from .minhash.models import (
    Event,
    EventType,
    SignatureFile,
    SignatureRecord,
    SimilarSignatures,
)
from .minhash.similarity import get_similar_signatures

LOG = logging.getLogger(__name__)

_SIGNATURE_STORE: SignatureRepository | None = None
_AUDIT_TRAIL_STORE: AuditTrailStore | None = None


def inject_store(store: SignatureRepository | AuditTrailStore) -> None:
    """Inject a SignatureStore instance for use in tasks."""
    global _SIGNATURE_STORE
    global _AUDIT_TRAIL_STORE

    if isinstance(store, SignatureRepository):
        if _SIGNATURE_STORE is not None:
            raise RuntimeError("SignatureStore has already been injected.")
        _SIGNATURE_STORE = store
    elif isinstance(store, AuditTrailStore):
        if _AUDIT_TRAIL_STORE is not None:
            raise RuntimeError("AuditTrailStore has already been injected.")
        _AUDIT_TRAIL_STORE = store
    else:
        raise TypeError(
            "store must be an instance of SignatureStore or AuditTrailStore"
        )


def get_signature_repo() -> SignatureRepository:
    """Get the injected SignatureStore instance."""
    if _SIGNATURE_STORE is None:
        raise RuntimeError(
            "SignatureStore has not been injected. Call inject_store() first."
        )
    return _SIGNATURE_STORE


def get_audit_trail_repo() -> AuditTrailStore:
    """Get the injected AuditTrailStore instance."""
    if _AUDIT_TRAIL_STORE is None:
        raise RuntimeError(
            "AuditTrailStore has not been injected. Call inject_store() first."
        )
    return _AUDIT_TRAIL_STORE


def add_signature(sample_id: str, signature: SignatureFile) -> str:
    """
    Find signatures similar to reference signature.

    :param sample_id str: the sample_id
    :param signature dict[str, str]: sourmash signature file in JSON format

    :return: path to the signature
    :rtype: str
    """
    at = get_audit_trail_repo()
    store = SignatureStorage(
        base_dir=settings.signature_dir, trash_dir=settings.trash_dir
    )
    repo = get_signature_repo()
    if repo.get_by_sample_id(sample_id) is not None:
        LOG.warning("Signature with sample_id %s already exists", sample_id)
        raise FileExistsError(f"Signature with sample_id {sample_id} already exists")

    # write signature to disk
    signature_path = write_signature(sample_id, signature, cnf=settings)
    signature_path = Path(signature_path)  # Ensure it's a Path object

    # upon completion write signature to the disk
    file_checksum = store.file_sha256_hex(signature_path)
    sharded_path = store.ensure_file(signature_path, file_checksum)

    # store as a signature record
    rec = SignatureRecord(
        sample_id=sample_id,
        signature_path=sharded_path,
        checksum=file_checksum,
    )
    try:
        repo.add_signature(rec)
    except Exception as err:
        LOG.error("Failed to add signature record for sample_id %s: %s", sample_id, err)
        # create audit trail event
        event = Event(event_type=EventType.ERROR, sample_id=sample_id, details=str(err))
        at.log_event(event)
        raise

    event = Event(
        event_type=EventType.UPLOAD,
        sample_id=sample_id,
        details="Signature added",
        metadata={"path": str(sharded_path)},
    )
    at.log_event(event)
    return str(sharded_path)


def remove_signature(sample_id: str) -> dict[str, str | bool]:
    """
    Remove a signature from the database and index.

    :param sample_id str: the sample_id of the signature to remove

    :return: The status of the removed job
    :rtype: Dict[str, str | bool]
    """
    repo = get_signature_repo()
    at = get_audit_trail_repo()
    store = SignatureStorage(
        base_dir=settings.signature_dir, trash_dir=settings.trash_dir
    )
    # mark sample for deletion in db
    was_marked = repo.marked_for_deletion(sample_id)
    if not was_marked:
        LOG.error(
            "Signature with sample_id %s could not be marked for deletion", sample_id
        )
        raise FileRemovalError(
            filepath=sample_id, reason="Could not be marked for deletion"
        )

    # stage file for removal
    record = repo.get_by_sample_id(sample_id)
    if record is None:
        LOG.error("No record found for sample_id %s", sample_id)
        raise FileNotFoundError(f"No record found for sample_id {sample_id}")

    metadata = {}
    try:
        repo.remove_by_sample_id(sample_id)
        # remove signature file if there are not other records with the same checksum
        if repo.count_by_checksum(record.checksum) == 0:
            removed_path = store.move_to_trash(record.signature_path, record.checksum)
            metadata["staged_path"] = str(removed_path)

        status = remove_signatures_from_index([sample_id], cnf=settings)

    except Exception as err:
        LOG.error("Failed to remove signature for sample_id %s: %s", sample_id, err)
        # log audit trail event
        e = Event(
            event_type=EventType.ERROR,
            sample_id=sample_id,
            details=str(err),
            metadata=metadata,
        )
        at.log_event(e)
        raise FileRemovalError(
            filepath=str(record.signature_path), reason=str(err)
        ) from err

    LOG.info("Signature with sample_id %s was removed", sample_id)
    e = Event(
        event_type=EventType.DELETE,
        sample_id=sample_id,
        details="Signature removed",
        metadata=metadata,
    )
    at.log_event(e)
    return {"sample_id": sample_id, "removed": status}


def check_signature(sample_id: str) -> dict[str, str | bool]:
    """Check if signature exist."""

    store = get_signature_repo()
    record = store.get_by_sample_id(sample_id)
    if record is None:
        raise FileNotFoundError(f"No record found for sample_id {sample_id}")

    return {
        "sample_id": sample_id,
        "exists": record.signature_path.exists(),
        "checksum": record.checksum,
        "indexed": record.has_been_indexed,
    }


def add_to_index(sample_ids: list[str]) -> str:
    """
    Add signatures to sourmash SBT index.

    :param sample_ids list[str]: The path to multiple signature files

    :return: result message
    :rtype: str
    """
    LOG.info("Adding %d signatures to index...", len(sample_ids))
    repo = get_signature_repo()
    signature_files: list[Path] = []
    # TODO query all signatures in one go
    for sample_id in sample_ids:
        record = repo.get_by_sample_id(sample_id)
        if record.exclude_from_analysis:
            LOG.info("Skipping excluded signature %s", sample_id)
            continue
        signature_files.append(record.signature_path)
    res, indexed_samples, warnings = add_signatures_to_index(signature_files, cnf=settings)
    # update indexed status in db
    for sid in indexed_samples:
        repo.mark_indexed(sid)

    signatures = ", ".join(list(sample_ids))
    if res:
        msg = f"Appended {signatures}"
        if warnings:
            warning_text = "; ".join(warnings)
            msg += f" (Warnings: {warning_text})"
    else:
        msg = f"Failed to append signatures, {signatures}"
        if warnings:
            warning_text = "; ".join(warnings)
            msg += f" (Warnings: {warning_text})"
    return msg


def remove_from_index(sample_ids: list[str]) -> str:
    """
    Remove signatures from sourmash SBT index.

    :param sample_ids list[str]: Sample ids of signatures to remove

    :return: result message
    :rtype: str
    """
    LOG.info("Removing signatures from index.")
    res = remove_signatures_from_index(sample_ids, cnf=settings)

    # unmark indexed status in db
    repo = get_signature_repo()
    for sid in sample_ids:
        repo.unmark_indexed(sid)

    signatures = ", ".join(list(sample_ids))
    if res:
        msg = f"Removed {signatures}"
    else:
        msg = f"Failed to remove signatures, {signatures}"
    return msg


def exclude_from_analysis(sample_ids: list[str]) -> str:
    """
    Exclude signatures from being included in analysis without removing them.

    :param sample_ids list[str]: Sample ids of signatures to exclude

    :return: result message
    :rtype: str
    """
    LOG.info("Excluding signatures %d from future analysis.", len(sample_ids))
    # unmark indexed status in db
    repo = get_signature_repo()
    for sid in sample_ids:
        repo.exclude_from_analysis(sid)

    signatures = ", ".join(list(sample_ids))
    msg = f"Excluded {signatures} from index"
    return msg


def similar(
    sample_id: str, min_similarity: float = 0.5, limit: int | None = None
) -> SimilarSignatures:
    """
    Find signatures similar to reference signature.

    :param sample_id str: The id of reference sample
    :param min_similarity float: Minimum similarity score
    :param limit int | None: Limit the result to x samples, default to None

    :return: list of the similar signatures
    :rtype: SimilarSignatures
    """
    repo = get_signature_repo()
    record = repo.get_by_sample_id(sample_id)
    if record is None:
        raise FileNotFoundError(f"No record found for sample_id {sample_id}")
    samples = get_similar_signatures(
        record.signature_path, min_similarity=min_similarity, limit=limit, cnf=settings
    )
    LOG.info(
        "Finding samples similar to %s with min similarity %s; limit %s",
        sample_id,
        min_similarity,
        limit,
    )
    results = [s.model_dump() for s in samples]
    return results


def cluster(sample_ids: list[str], cluster_method: str = "single") -> str:
    """
    Cluster multiple sample on their sourmash signatures.

    :param sample_ids list[str]: The sample ids to cluster
    :param cluster_method int: The linkage or clustering method to use, default to single

    :raises ValueError: raises an exception if the method is not a valid MSTree clustering method.

    :return: clustering result in newick format
    :rtype: str
    """
    # validate input
    try:
        method = ClusterMethod(cluster_method)
    except ValueError as error:
        msg = f'"{cluster_method}" is not a valid cluster method'
        LOG.error(msg)
        raise ValueError(msg) from error
    # cluster
    repo = get_signature_repo()
    signature_files: list[Path] = []
    for sample_id in sample_ids:
        record = repo.get_by_sample_id(sample_id)
        signature_files.append(record.signature_path)
    newick: str = cluster_signatures(signature_files, method, cnf=settings)
    return newick


def find_similar_and_cluster(
    sample_id: str,
    min_similarity: float = 0.5,
    limit: int | None = None,
    cluster_method: str = "single",
) -> str:
    """
    Find similar samples and cluster them on their minhash profile.

    :param sample_id str: The id of reference sample
    :param min_similarity float: Minimum similarity score
    :param limit int | None: Limit the result to x samples, default to None
    :param cluster_method int: The linkage or clustering method to use, default to single

    :raises ValueError: raises an exception if the method is not a valid MSTree clustering method.

    :return: clustering result in newick format
    :rtype: str
    """
    # validate input
    try:
        method = ClusterMethod(cluster_method)
    except ValueError as error:
        msg = f'"{cluster_method}" is not a valid cluster method'
        LOG.error(msg)
        raise ValueError(msg) from error
    LOG.info(
        "Finding samples similar to %s with min similarity %s; limit %s",
        sample_id,
        min_similarity,
        limit,
    )
    repo = get_signature_repo()
    record = repo.get_by_sample_id(sample_id)
    sample_ids = get_similar_signatures(
        record.signature_path, min_similarity=min_similarity, limit=limit, cnf=settings
    )

    # if 1 or 0 samples were found, return emtpy newick
    if len(sample_ids) < 2:
        LOG.warning("Invalid number of samples found, %d", len(sample_ids))
        return "()"
    repo = get_signature_repo()
    signature_files: list[Path] = []
    for sample_sig in sample_ids:
        record = repo.get_by_sample_id(sample_sig.sample_id)
        signature_files.append(record.signature_path)
    # cluster samples
    sids = [sid.sample_id for sid in sample_ids]
    LOG.info(
        "Clustering the following samples to %s: ",
        ", ".join(sids),
    )
    newick: str = cluster_signatures(signature_files, method, cnf=settings)
    return newick
