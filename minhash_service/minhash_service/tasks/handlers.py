"""Define reddis tasks."""

import datetime as dt
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Iterable, cast

from minhash_service.analysis.cluster import cluster_signatures
from minhash_service.analysis.models import (
    AniEstimateOptions,
    ClusterMethod,
    SimilaritySearchConfig,
    SimilarSignature,
    SimilarSignatures,
)
from minhash_service.analysis.similarity import get_similar_signatures
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
from minhash_service.signatures.io import read_signatures, write_signatures
from minhash_service.signatures.models import SignatureRecord, SourmashSignatures
from minhash_service.signatures.repository import SignatureRepository
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
    if repo.get_by_sample_id_or_checksum(sample_id=sample_id) is not None:
        LOG.warning("Signature with sample_id %s already exists", sample_id)
        raise FileExistsError(f"Signature with sample_id {sample_id} already exists")

    # write signature to disk
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)
        tmp_sig_path = tmp_dir / f"{sample_id}.sig"
        signature_path = write_signatures(
            path=tmp_sig_path, signature=signature, kmer_size=cnf.kmer_size
        )

    # upon completion write signature to the disk
    file_checksum = store.file_sha256_hex(signature_path)
    sharded_path = store.ensure_file(signature_path, file_checksum)

    # store signature checksum in database
    loaded_sig = read_signatures(sharded_path, cnf.kmer_size)[0]

    # store as a signature record
    record = SignatureRecord(
        sample_id=sample_id,
        signature_path=sharded_path,
        signature_checksum=cast(str, loaded_sig.md5sum()),
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
        if repo.count_by_checksum(record.signature_checksum) == 0:
            removed_path = store.move_to_trash(
                record.signature_path, record.signature_checksum
            )
            metadata["staged_path"] = str(removed_path)

        result = index.remove_signatures(set([record.signature_checksum]))

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


def check_signature(sample_id: str) -> dict[str, str | bool]:
    """Check if signature exist."""

    repo = create_signature_repo()
    record = repo.get_by_sample_id_or_checksum(sample_id=sample_id)
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
    Add signatures to sourmash index.

    :param sample_ids list[str]: The path to multiple signature files

    :return: result message
    :rtype: str
    """
    LOG.info("Adding %d signatures to index...", len(sample_ids))
    repo = create_signature_repo()

    signatures = _load_signatures_from_sample_id(sample_ids)

    # add to index
    idx_path = get_index_path(cnf.signature_dir, cnf.index_format)
    index = create_index_store(idx_path, index_format=cnf.index_format)
    result = index.add_signatures(signatures)

    LOG.info(
        "Updating index status in the database for %d samples.", result.added_count
    )
    update_status: dict[str, bool] = {}
    for checksum in result.added_md5s:
        rec = repo.get_by_sample_id_or_checksum(checksum=checksum)
        status = repo.mark_indexed(rec.sample_id)
        update_status[rec.sample_id] = status

    all_updated: bool = all(status for status in update_status.values())
    if not all_updated:
        failed_update = [name for name, status in update_status.items() if not status]
        LOG.error(
            "Failed to mark %d samples as indexed; %s",
            len(failed_update),
            ", ".join(failed_update),
        )
    else:
        LOG.debug("Marked %d samples as indexed", len(update_status))

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

    # lookup checksums for sample ids
    repo = create_signature_repo()
    checksums_to_remove: list[str] = []
    md5_to_sample_id: dict[str, str] = {}
    for sid in sample_ids:
        sample = repo.get_by_sample_id_or_checksum(sample_id=sid)
        if sample is None:
            continue
        checksum = sample.signature_checksum
        md5_to_sample_id[checksum] = sid
        checksums_to_remove.append(checksum)

    result = index.remove_signatures(set(checksums_to_remove))
    if not result.ok:
        n_remaining = len(checksums_to_remove) - result.removed_count
        LOG.error("Failed to remove %d checksum from index", n_remaining)

    # unmark indexed status in db
    repo = create_signature_repo()
    for sid in sample_ids:
        repo.unmark_indexed(sid)
    return result.model_dump()


def exclude_from_analysis(sample_ids: list[str]) -> dict[str, bool | list[str]]:
    """
    Exclude signatures from being included in analysis without removing them.

    :param sample_ids list[str]: Sample ids of signatures to exclude

    :return: result message
    :rtype: str
    """
    LOG.info("Excluding %d signatures from future analysis.", len(sample_ids))
    # unmark indexed status in db
    excluded_samples: list[str] = []
    repo = create_signature_repo()
    for sid in sample_ids:
        status = repo.exclude_from_analysis(sid)
        if status:
            excluded_samples.append(sid)

    all_ok = len(excluded_samples) == len(sample_ids)
    return {"ok": all_ok, "excluded": excluded_samples, "to_exclude": sample_ids}


def include_in_analysis(sample_ids: list[str]) -> dict[str, str | bool | list[str]]:
    """
    Include signatures in downstream analysis.

    :param sample_ids list[str]: Sample ids of signatures to exclude

    :return: result message
    :rtype: str
    """
    LOG.info("Including %d signatures in future analysis.", len(sample_ids))
    # unmark indexed status in db
    repo = create_signature_repo()

    included: list[str] = []
    for sid in sample_ids:
        status = repo.include_in_analysis(sid)
        if status:
            included.append(sid)

    all_ok = len(included) == len(sample_ids)
    return {"ok": all_ok, "included": included, "to_include": sample_ids}


def _lookup_checksums_from_sample_ids(
    sample_ids: Iterable[str] | None, repo: SignatureRepository
) -> list[str] | None:
    """Lookup checksums for sample ids."""
    if sample_ids is None:
        return None

    return [
        rec.signature_checksum
        for sid in sample_ids
        if (rec := repo.get_by_sample_id_or_checksum(sample_id=sid))
    ]


def _load_signatures_from_sample_id(sample_ids: list[str]) -> SourmashSignatures:
    """Load signatures from sample ids."""
    LOG.debug("Load signatures to memory")
    repo = create_signature_repo()

    signatures: SourmashSignatures = []
    for sample_id in sample_ids:
        record = repo.get_by_sample_id_or_checksum(sample_id=sample_id)
        if record is None:
            LOG.error("No signature for sample id: %s", sample_id)
            continue

        if record.exclude_from_analysis:
            LOG.info("Skipping excluded signature %s", sample_id)
            continue

        signature = read_signatures(record.signature_path, kmer_size=cnf.kmer_size)
        signatures.extend(signature)  # append to all signatures
    return signatures


def search_similar(
    sample_id: str,
    estimate_ani: AniEstimateOptions = AniEstimateOptions.JACCARD,
    min_similarity: float = 0.5,
    limit: int | None = None,
    subset_sample_ids: list[str] | None = None,
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
    record = repo.get_by_sample_id_or_checksum(sample_id=sample_id)
    if record is None:
        raise FileNotFoundError(f'No record found for sample_id: "{sample_id}"')

    # is allways one sig
    query = read_signatures(record.signature_path, kmer_size=cnf.kmer_size)[0]

    # check if signature is empty
    if len(query.minhash) == 0:
        raise ValueError("Cant perform search, No query hashes?")

    # get index store
    index = create_index_store(
        get_index_path(cnf.signature_dir, cnf.index_format),
        index_format=cnf.index_format,
    )

    # build search config
    subset_checksums = _lookup_checksums_from_sample_ids(subset_sample_ids, repo)
    search_cnf = SimilaritySearchConfig(
        min_similarity=min_similarity,
        limit=limit,
        ani_estimate=estimate_ani,
        subset_checksums=subset_checksums,
    )

    # lookup sample ids from matches
    similarity_result: SimilarSignatures = []
    for res in get_similar_signatures(query, index, search_cnf):
        # enforce limit
        if limit is not None and len(similarity_result) >= limit:
            break

        # optionally skip samples that are not in subset
        match_checksum = cast(str, res.match.md5sum())
        if subset_checksums is not None and match_checksum not in subset_checksums:
            continue

        # use matched signature checksum to lookup the sample
        sample = repo.get_by_sample_id_or_checksum(checksum=match_checksum)
        if sample is None:
            LOG.warning("Could not find a sample with checksum: %s", match_checksum)
            raise SampleNotFoundError(
                f"Cant find a sample with checksum: {match_checksum}"
            )
        # recast result to a internally maintained data type
        similarity_result.append(
            SimilarSignature(sample_id=sample.sample_id, similarity=res.similarity)
        )

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
    LOG.info("Prepare to cluster %d signatures", len(sample_ids))
    try:
        method = ClusterMethod(cluster_method)
    except ValueError as error:
        msg = f'"{cluster_method}" is not a valid cluster method'
        LOG.error(msg)
        raise ValueError(msg) from error

    # load sequence signatures to memory
    signatures = _load_signatures_from_sample_id(sample_ids)

    LOG.info("Cluster %d signatures", len(sample_ids))
    newick: str = cluster_signatures(signatures, method)
    return newick


def find_similar_and_cluster(
    sample_id: str,
    min_similarity: float = 0.5,
    limit: int | None = None,
    subset_sample_ids: list[str] | None = None,
    cluster_method: str = "single",
) -> str:
    """
    Find similar samples and cluster them on their minhash profile.

    :param sample_id str: The id of reference sample
    :param min_similarity float: Minimum similarity score
    :param limit int | None: Limit the result to x samples, default to None
    :param cluster_method int: The linkage or clustering method to use, default to single
    :param subset_sample_ids list[str] | None: Narrow the search to the following ids

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
    results = search_similar(
        sample_id=sample_id,
        min_similarity=min_similarity,
        limit=limit,
        subset_sample_ids=subset_sample_ids,
    )
    LOG.info("Found %d similar samples", len(results))

    # if 1 or 0 samples were found, return emtpy newick
    if len(results) < 2:
        LOG.warning("Invalid number of samples found, %d", len(results))
        return "()"

    # load sequence signatures to memory
    repo = create_signature_repo()
    sample_ids: list[str] = []
    for res in results:
        record = repo.get_by_sample_id_or_checksum(sample_id=res["sample_id"])
        if record is None:
            continue
        sample_ids.append(record.sample_id)
    signatures = _load_signatures_from_sample_id(sample_ids)

    # cluster samples
    LOG.info("Cluster samples...")
    newick: str = cluster_signatures(signatures, method)
    return newick


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
    return None


def cleanup_removed_files() -> None:
    """Cleanup files marked for removal."""
    two_weeks_ago: dt.datetime = dt.datetime.now(dt.UTC) - dt.timedelta(weeks=2)

    store = SignatureStorage(base_dir=cnf.signature_dir, trash_dir=cnf.trash_dir)
    n_removed = store.purge_older_than(cutoff=two_weeks_ago)
    LOG.info("Cleanup removed %d files", n_removed)
