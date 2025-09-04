"""Define reddis tasks."""

import datetime as dt
import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from minhash_service.analysis.cluster import ClusterMethod, cluster_signatures, tree_to_newick
from minhash_service.analysis.similarity import get_similar_signatures
from minhash_service.analysis.models import SimilarSignatures, AniEstimateOptions, SimilarSignature
from minhash_service.core.config import IntegrityReportLevel, cnf
from minhash_service.core.exceptions import FileRemovalError, SampleNotFoundError
from minhash_service.core.factories import (
    create_audit_trail_repo,
    create_report_repo,
    create_signature_repo,
)
from minhash_service.core.models import Event, EventType
from minhash_service.integrity.checker import check_signature_integrity
from minhash_service.integrity.report_model import InitiatorType
from minhash_service.signatures.index import create_index_store, get_index_path
from minhash_service.signatures.io import (
    read_signatures,
    write_signatures,
)
from minhash_service.signatures.models import (
    IndexFormat,
    SignatureRecord,
    SourmashSignatures,
)
from minhash_service.signatures.storage import SignatureStorage

from .notify import EmailApiInput, dispatch_email

LOG = logging.getLogger(__name__)


def add_signature(sample_id: str, signature: str) -> str:
    """
    Find signatures similar to reference signature.

    :param sample_id str: the sample_id
    :param signature str: MUST be a JSON sting in sourmash signature format

    :return: path to the signature
    :rtype: str
    """
    # validate signature
    try:
        json.loads(signature)
    except json.JSONDecodeError as err:
        LOG.debug("Malformed JSON file format: %s", signature)
        raise ValueError("signature is not a valid JSON string") from err
    
    # setup repositories
    at = create_audit_trail_repo()
    store = SignatureStorage(base_dir=cnf.signature_dir, trash_dir=cnf.trash_dir)
    repo = create_signature_repo()

    if repo.get_by_sample_id_or_checksum(sample_id) is not None:
        LOG.warning("Signature with sample_id %s already exists", sample_id)
        raise FileExistsError(f"Signature with sample_id {sample_id} already exists")

    # write signature to disk
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_file = Path(tmp_dir) / "signature.sig"
        signature_path = write_signatures(tmp_file, signature, kmer_size=cnf.kmer_size)

        signature_path = Path(signature_path)  # Ensure it's a Path object

        # upon completion write signature to the disk
        file_checksum = store.file_sha256_hex(signature_path)
        sharded_path = store.ensure_file(signature_path, file_checksum)

    # store signature checksum in database
    loaded_sig = read_signatures(sharded_path, cnf.kmer_size)[0]

    # store as a signature record
    record = SignatureRecord(
        sample_id=sample_id,
        signature_path=sharded_path,
        signature_checksum=loaded_sig.md5sum(),
        file_checksum=file_checksum,
    )
    try:
        repo.add_signature(record)
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
    at = create_audit_trail_repo()
    repo = create_signature_repo()
    store = SignatureStorage(base_dir=cnf.signature_dir, trash_dir=cnf.trash_dir)
    # get index store
    idx_path = get_index_path(cnf.signature_dir, cnf.index_format)
    index = create_index_store(idx_path, cnf.index_format)
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
    record = repo.get_by_sample_id_or_checksum(sample_id)
    if record is None:
        LOG.error("No record found for sample_id %s", sample_id)
        raise FileNotFoundError(f"No record found for sample_id {sample_id}")

    metadata: dict[str, str] = {}

    try:
        repo.remove_by_sample_id(sample_id)
        # remove signature file if there are not other records with the same checksum
        if repo.count_by_checksum(record.checksum) == 0:
            removed_path = store.move_to_trash(record.signature_path, record.checksum)
            metadata["staged_path"] = str(removed_path)

        result = index.remove_signatures([sample_id])

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
    return result.model_dump(mode="json")


def add_to_index(sample_ids: list[str]) -> dict[str, Any]:
    """
    Add signatures to sourmash index.

    :param sample_ids list[str]: The path to multiple signature files

    :return: result message
    :rtype: str
    """
    LOG.info("Adding %d signatures to index...", len(sample_ids))
    repo = create_signature_repo()

    loaded_signatures: SourmashSignatures = []
    sample_to_md5s: dict[str, list[str]] = {}

    # load subset of signatures with SBT index as it can append to exising index
    if cnf.index_format == IndexFormat.SBT:
        # TODO query all signatures in one go
        for sample_id in sample_ids:
            record = repo.get_by_sample_id_or_checksum(sample_id)
            if record is None:
                LOG.warning("No signature stored for %s", sample_id)
                continue

            if record.exclude_from_analysis:
                LOG.info("Skipping excluded signature %s", sample_id)
                continue
            sig = read_signatures(record.signature_path, cnf.kmer_size)
            # store md5 sums for sample
            md5s_for_sample: list[str] = [s.md5sum() for s in sig]
            sample_to_md5s[sample_id] = md5s_for_sample

            loaded_signatures.extend(sig)
    else:
        # rebuild entire index if using RocksDB index
        for record in repo.get_all_signatures():
            sig = read_signatures(record.signature_path, cnf.kmer_size)
            md5s_for_sample: list[str] = [s.md5sum() for s in sig]
            sample_to_md5s[record.sample_id] = md5s_for_sample
            loaded_signatures.extend(sig)

    # read signatures to memory
    idx_path = get_index_path(cnf.signature_dir, cnf.index_format)
    index = create_index_store(idx_path, index_format=cnf.index_format)
    result = index.add_signatures(loaded_signatures)

    # update indexed status in db
    indexed_samples: list[str] = [
        sid
        for sid, md5s in sample_to_md5s.items()
        if any(md5 in result.added_md5s for md5 in md5s)
    ]
    LOG.info(
        "Updating index status in the database for %d samples.", len(indexed_samples)
    )
    for sid in indexed_samples:
        repo.mark_indexed(sid)

    return result.model_dump(mode="json")


def remove_from_index(sample_ids: list[str]) -> dict[str, Any]:
    """
    Remove signatures from a sourmash index.

    :param sample_ids list[str]: Sample ids of signatures to remove

    :return: result message
    :rtype: str
    """
    LOG.info("Removing signatures from index.")
    # get index store
    idx_path = get_index_path(cnf.signature_dir, cnf.index_format)
    index = create_index_store(idx_path, index_format=cnf.index_format)
    result = index.remove_signatures(sample_ids)

    # unmark indexed status in db
    repo = create_signature_repo()

    for sid in sample_ids:
        repo.unmark_indexed(sid)
    return result.model_dump()

def exclude_from_analysis(sample_ids: list[str]) -> str:
    """
    Exclude signatures from being included in analysis without removing them.

    :param sample_ids list[str]: Sample ids of signatures to exclude

    :return: result message
    :rtype: str
    """
    LOG.info("Excluding signatures %d from future analysis.", len(sample_ids))
    # unmark indexed status in db
    repo = create_signature_repo()

    for sid in sample_ids:
        repo.exclude_from_analysis(sid)

    signatures = ", ".join(list(sample_ids))
    msg = f"Excluded {signatures} from index"
    return msg


def search_similar(
    sample_id: str, estimate_ani: AniEstimateOptions = AniEstimateOptions.JACCARD, min_similarity: float = 0.5, limit: int | None = None
) -> list[dict[str, Any]]:
    """
    Find signatures similar to reference signature.

    :param sample_id str: The id of reference sample
    :param min_similarity float: Minimum similarity score
    :param limit int | None: Limit the result to x samples, default to None

    :return: list of the similar signatures
    :rtype: SimilarSignatures
    """
    repo = create_signature_repo()

    record = repo.get_by_sample_id_or_checksum(sample_id)
    if record is None:
        raise FileNotFoundError(f"No record found for sample_id {sample_id}")

    # is allways one sig
    query = read_signatures(record.signature_path, kmer_size=cnf.kmer_size)[0]

    # check if signature is empty
    if len(query.minhash) == 0:
        raise ValueError("Cant perform search, No query hashes?")

    # get index store
    idx_path = get_index_path(cnf.signature_dir, cnf.index_format)
    index = create_index_store(idx_path, index_format=cnf.index_format)

    results = get_similar_signatures(
        query, index, ani_estimate=estimate_ani, min_similarity=min_similarity, limit=limit
    )
    # lookup sample ids from matches
    similarity_result: SimilarSignatures = []
    for res in results:
        # enforce limit
        if len(similarity_result) > limit:
            break

        # use matched signature checksum to lookup the sample
        match_checksum = res.match.md5sum()
        sample = repo.get_by_sample_id_or_checksum(checksum=match_checksum)
        if sample is None:
            LOG.warning("Could not find a sample with checksum: %s", match_checksum)
            raise SampleNotFoundError(f"Cant find a sample with checksum: {match_checksum}")
        # recast result to a internally maintained data type
        upd_res = SimilarSignature(sample_id=sample.sample_id, similarity=res.similarity)
        similarity_result.append(upd_res)
    LOG.info(
        "Finding samples similar to %s with min similarity %s; limit %s",
        sample_id,
        min_similarity,
        limit,
    )
    return [s.model_dump(mode="json") for s in similarity_result]


def cluster_samples(sample_ids: list[str], cluster_method: str = "single") -> str:
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
    repo = create_signature_repo()
    signature_files: list[Path] = []
    md5_to_sample_id: dict[str, str] = {}
    for sample_id in sample_ids:
        record = repo.get_by_sample_id_or_checksum(sample_id)
        if record is None:
            LOG.error("No signature for sample id: %s", sample_id)
            continue
        signature_files.append(record.signature_path)
        md5_to_sample_id[record.signature_checksum] = record.sample_id
    tree, included_checksums = cluster_signatures(signature_files, method, kmer_size=cnf.kmer_size)
    # create tree labels
    label_text = [md5_to_sample_id[md5] for md5 in included_checksums]
    newick_tree = tree_to_newick(tree, "", tree.dist, label_text)
    return newick_tree


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
    results = search_similar(sample_id=sample_id, min_similarity=min_similarity, limit=limit)
    LOG.info("Found %d similar samples", len(results))

    # if 1 or 0 samples were found, return emtpy newick
    if len(results) < 2:
        LOG.warning("Invalid number of samples found, %d", len(results))
        return "()"

    sample_ids = [res['sample_id'] for res in results]
    newick = cluster_samples(sample_ids=sample_ids, cluster_method=method)

    return newick


def check_signature(sample_id: str) -> dict[str, str | bool]:
    """Check if signature exist."""

    repo = create_signature_repo()
    record = repo.get_by_sample_id_or_checksum(sample_id)

    if record is None:
        raise FileNotFoundError(f"No record found for sample_id {sample_id}")

    return {
        "sample_id": sample_id,
        "exists": record.signature_path.exists(),
        "checksum": record.checksum,
        "indexed": record.has_been_indexed,
    }


def run_data_integrity_check() -> None:
    """Check integrity of the minhash service and save report to db."""

    report = check_signature_integrity(InitiatorType.SYSTEM, cnf)
    repo = create_report_repo()
    LOG.info("Saving report to database")
    repo.save(report)

    report_error = (
        cnf.notification.integrity_report_level == IntegrityReportLevel.ERROR
        and report.has_errors
    )
    report_warning = all(
        [
            cnf.notification.integrity_report_level == IntegrityReportLevel.WARNING,
            report.has_errors or report.has_warnings,
        ]
    )
    if cnf.is_notification_configured and (report_error or report_warning):
        # notify admins of errror
        message = EmailApiInput(
            recipient=cnf.notification.recipient, subject="MinHash Integrity report"
        )
        dispatch_email(str(cnf.notification.api_url), message)


def get_data_integrity_report() -> dict[str, Any] | None:
    """Check integrity of the minhash service and save report to db."""

    LOG.info("Get last integrity report from the database")
    repo = create_report_repo()
    report = repo.get_latest()
    if report is not None:
        return report.model_dump(mode="json")


def cleanup_removed_files() -> None:
    """Cleanup files marked for removal."""
    two_weeks_ago: dt.datetime = dt.datetime.now(dt.UTC) - dt.timedelta(weeks=2)

    store = SignatureStorage(base_dir=cnf.signature_dir, trash_dir=cnf.trash_dir)
    n_removed = store.purge_older_than(cutoff=two_weeks_ago)
    LOG.info("Cleanup removed %d files", n_removed)
