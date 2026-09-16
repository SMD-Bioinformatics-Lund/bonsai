"""Define reddis tasks."""

import datetime as dt
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Iterable, cast

from minhash_service.analysis.cluster import cluster_signatures, tree_to_newick
from minhash_service.analysis.models import (AniEstimateOptions, ClusterMethod,
                                             SimilarResult,
                                             SimilaritySearchConfig,
                                             SimilarSampleResult)
from minhash_service.analysis.similarity import get_similar_signatures
from minhash_service.core.config import IntegrityReportLevel, cnf
from minhash_service.core.exceptions import FileRemovalError
from minhash_service.core.factories import (create_audit_trail_repo,
                                            create_report_repo,
                                            create_signature_repo)
from minhash_service.core.models import Event, EventType
from minhash_service.integrity.checker import check_signature_integrity
from minhash_service.integrity.report_model import InitiatorType
from minhash_service.signatures.index import (RemoveResult, create_index_store,
                                              get_index_path)
from minhash_service.signatures.io import read_signatures, write_signatures
from minhash_service.signatures.models import (SignatureRecord,
                                               SourmashSignatures)
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
    records = repo.get_by_sample_id_or_checksum(sample_id=sample_id)
    if len(records) > 0:
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
    loaded_sigs = read_signatures(sharded_path)
    for sig in loaded_sigs:
        record = SignatureRecord(
            sample_id=sample_id,
            kmer_size=sig.minhash.ksize,
            signature_path=sharded_path,
            signature_checksum=cast(str, sig.md5sum()),
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
    records = repo.get_by_sample_id_or_checksum(sample_id)
    if records is None or len(records) == 0:
        LOG.error("No record found for sample_id %s", sample_id)
        raise FileNotFoundError(f"No record found for sample_id {sample_id}")

    metadata: dict[str, str] = {}
    rec = records[0]
    try:
        repo.remove_by_sample_id(sample_id)
        remaining_records = repo.count_by_checksum(rec.signature_checksum)
        # Keep shared files and index entries until the final sample using the
        # checksum is removed.
        if remaining_records == 0:
            removed_path = store.move_to_trash(
                rec.signature_path, rec.signature_checksum
            )
            metadata["staged_path"] = str(removed_path)
            result = index.remove_signatures({rec.signature_checksum})
        else:
            result = RemoveResult(
                is_successful=True,
                warnings=[],
                removed_count=0,
                removed=[],
            )

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
            filepath=str(rec.signature_path), reason=str(err)
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
    records = repo.get_by_sample_id_or_checksum(sample_id=sample_id)
    if records is None:
        raise FileNotFoundError(f"No record found for sample_id {sample_id}")

    rec_info = []
    for r in records:
        rec_info.append({
            "exists": r.signature_path.exists(),
            "checksum": r.checksum,
            "indexed": r.has_been_indexed,
        })
    return {
        "sample_id": sample_id,
        "records": rec_info
    }


def add_to_index(sample_ids: list[str]) -> dict[str, Any]:
    """
    Add signatures to sourmash index.

    :param sample_ids list[str]: The path to multiple signature files

    :return: result message
    :rtype: str
    """
    kmer_size = cnf.kmer_size
    LOG.info("Adding %d signatures to index...", len(sample_ids))
    repo = create_signature_repo()

    indexable_sample_ids: list[str] = []
    for sample_id in sample_ids:
        records = repo.get_by_sample_id_or_checksum(
            sample_id=sample_id, kmer_size=kmer_size
        )
        if len(records) == 1 and not records[0].exclude_from_analysis and not records[0].marked_for_deletion:
            indexable_sample_ids.append(sample_id)

    signatures = _load_signatures_from_sample_id(sample_ids, kmer_size=kmer_size)

    # add to index
    idx_path = get_index_path(cnf.signature_dir, cnf.index_format)
    index = create_index_store(idx_path, index_format=cnf.index_format)
    result = index.add_signatures(signatures)

    if not result.is_successful:
        raise RuntimeError(f"Failed to add signatures to the index: {result.warnings}")

    LOG.info(
        "Updating index status in the database for %d samples.",
        len(indexable_sample_ids),
    )
    _set_index_status(repo, indexable_sample_ids, kmer_size=kmer_size, indexed=True)
    LOG.debug("Marked %d samples as indexed", len(indexable_sample_ids))

    return result.model_dump(mode="json")


def _set_index_status(
    repo: SignatureRepository,
    sample_ids: Iterable[str],
    *,
    kmer_size: int,
    indexed: bool,
) -> None:
    failed = [
        sid
        for sid in dict.fromkeys(sample_ids)
        if not repo.set_indexed(sid, kmer_size, indexed)
    ]
    if failed:
        raise RuntimeError(
            f"Could not update index status for samples: {', '.join(failed)}"
        )


def rebuild_index(kmer_size: int | None = None) -> dict[str, Any]:
    """Rebuild from eligible metadata without reading the historical index.

    Run with import/QC/deletion workers paused so metadata remains stable.
    Validate every input before replacing the index or changing any flags.
    """
    kmer_size = kmer_size or cnf.kmer_size
    if kmer_size != cnf.kmer_size:
        raise ValueError("The index must use the configured k-mer size")
    repo = create_signature_repo()
    records = [r for r in repo.get_all_signatures() if r.kmer_size == kmer_size]
    eligible = [
        r for r in records if not r.exclude_from_analysis and not r.marked_for_deletion
    ]
    signatures: SourmashSignatures = []
    for record in eligible:
        loaded = read_signatures(record.signature_path, kmer_size=kmer_size)
        if len(loaded) != 1 or loaded[0].md5sum() != record.signature_checksum:
            raise ValueError(f"Invalid signature for sample {record.sample_id}")
        signatures.extend(loaded)
    index = create_index_store(
        get_index_path(cnf.signature_dir, cnf.index_format), cnf.index_format
    )
    result = index.replace_signatures(signatures)
    if not result.is_successful:
        raise RuntimeError(f"Failed to rebuild index: {result.warnings}")
    eligible_ids = {r.sample_id for r in eligible}
    for indexed in (True, False):
        _set_index_status(
            repo,
            [r.sample_id for r in records if (r.sample_id in eligible_ids) == indexed],
            kmer_size=kmer_size,
            indexed=indexed,
        )
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
    removed_ids = set(sample_ids)
    records = [
        record
        for sid in removed_ids
        for record in repo.get_by_sample_id_or_checksum(
            sample_id=sid, kmer_size=cnf.kmer_size
        )
    ]
    checksums_to_remove = {r.signature_checksum for r in records}
    for checksum in list(checksums_to_remove):
        others = repo.get_by_sample_id_or_checksum(
            checksum=checksum, kmer_size=cnf.kmer_size
        )
        if any(
            r.sample_id not in removed_ids
            and not r.exclude_from_analysis
            and not r.marked_for_deletion
            for r in others
        ):
            checksums_to_remove.remove(checksum)

    # Retrying after a metadata-update failure must still reconcile flags,
    # even if the previous attempt already removed the index entry.
    if checksums_to_remove:
        if index.index_path.exists():
            checksums_to_remove.intersection_update(index.list_signature_checksums())
        else:
            checksums_to_remove.clear()

    result = (
        index.remove_signatures(checksums_to_remove)
        if checksums_to_remove
        else RemoveResult(is_successful=True, warnings=[], removed_count=0, removed=[])
    )
    if not result.is_successful:
        raise RuntimeError(f"Failed to remove signatures from index: {result.warnings}")

    # unmark indexed status in db
    _set_index_status(
        repo, [r.sample_id for r in records], kmer_size=cnf.kmer_size, indexed=False
    )
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

    checksums: list[str] = []
    for sample_id in sample_ids:
        records = repo.get_by_sample_id_or_checksum(sample_id=sample_id)
        checksums.extend(record.signature_checksum for record in records)
    return list(dict.fromkeys(checksums))


def _resolve_sample_matches(
    matches: list[SimilarResult],
    repo: SignatureRepository,
    *,
    kmer_size: int,
    subset_sample_ids: Iterable[str] | None = None,
    limit: int | None = None,
) -> list[SimilarSampleResult]:
    """Expand signature matches into unique, eligible sample matches."""
    allowed_sample_ids = set(subset_sample_ids) if subset_sample_ids is not None else None
    resolved: list[SimilarSampleResult] = []
    seen_sample_ids: set[str] = set()

    if limit is not None and limit <= 0:
        return []

    for match in matches:
        records = repo.get_by_sample_id_or_checksum(
            checksum=match.md5, kmer_size=kmer_size
        )
        for record in sorted(records, key=lambda item: item.sample_id):
            if record.exclude_from_analysis or record.marked_for_deletion:
                continue
            if allowed_sample_ids is not None and record.sample_id not in allowed_sample_ids:
                continue
            if record.sample_id in seen_sample_ids:
                continue

            resolved.append(
                SimilarSampleResult(
                    sample_id=record.sample_id,
                    signature_checksum=match.md5,
                    containment=match.containment,
                    jaccard_similarity=match.jaccard_similarity,
                    max_containment=match.max_containment,
                )
            )
            seen_sample_ids.add(record.sample_id)
            if limit is not None and len(resolved) >= limit:
                return resolved

    return resolved


def _load_signatures_from_sample_id(sample_ids: list[str], kmer_size: int | None = None) -> SourmashSignatures:
    """Load signatures from sample ids."""
    LOG.debug("Load signatures to memory")
    repo = create_signature_repo()

    signatures: SourmashSignatures = []
    for sample_id in sample_ids:
        records = repo.get_by_sample_id_or_checksum(sample_id=sample_id, kmer_size=kmer_size)

        if not records:
            LOG.error("No signature found for sample_id=%s", sample_id)
            continue

        if len(records) > 1:
            LOG.error(
                "Multiple signature records for sample_id=%s; kmer_size=%s",
                sample_id,
                kmer_size,
            )
            continue

        record = records[0]

        if record.exclude_from_analysis or record.marked_for_deletion:
            LOG.info("Skipping excluded signature %s", sample_id)
            continue

        sigs = read_signatures(record.signature_path, kmer_size=kmer_size)
        signatures.extend(sigs)  # append to all signatures
    return signatures


def search_similar(
    sample_id: str,
    estimate_ani: AniEstimateOptions = AniEstimateOptions.JACCARD,
    min_similarity: float = 0.5,
    limit: int | None = None,
    subset_sample_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Find signatures similar to reference signature.

    :param sample_id str: The id of reference sample
    :param min_similarity float: Minimum similarity score
    :param limit int | None: Limit the result to x samples, default to None

    :return: list of the similar signatures
    :rtype: SimilarSignatures
    """
    kmer_size = cnf.kmer_size
    repo = create_signature_repo()
    records = repo.get_by_sample_id_or_checksum(sample_id=sample_id, kmer_size=kmer_size)
    if not records:
        raise FileNotFoundError(f'No record found for sample_id: "{sample_id}"')
    
    record = records[0]

    index = create_index_store(
        get_index_path(cnf.signature_dir, cnf.index_format),
        index_format=cnf.index_format,
    )

    # build search config
    subset_checksums = _lookup_checksums_from_sample_ids(subset_sample_ids, repo)
    search_cnf = SimilaritySearchConfig(
        min_similarity=min_similarity,
        # Limit after resolving checksums to sample IDs. A checksum can belong
        # to multiple samples and duplicate index entries must not consume the
        # user-facing sample limit.
        limit=None,
        ani_estimate=estimate_ani,
        subset_checksums=subset_checksums,
        ksize=kmer_size
    )

    # lookup sample ids from matches
    result = get_similar_signatures(record.signature_path, index, search_cnf)
    matches = _resolve_sample_matches(
        result.matches,
        repo,
        kmer_size=kmer_size,
        subset_sample_ids=subset_sample_ids,
        limit=limit,
    )
    LOG.info(
        "Finding samples similar to %s with min similarity %s; limit %s",
        sample_id,
        min_similarity,
        limit,
    )
    response = result.model_dump(mode="json")
    response["matches"] = [match.model_dump(mode="json") for match in matches]
    return response


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
    tree, checksums  = cluster_signatures(signatures, method)

    repo = create_signature_repo()
    kmer_size = cnf.kmer_size
    sample_ids = []
    for checksum in checksums:
        records = repo.get_by_sample_id_or_checksum(checksum=checksum, kmer_size=kmer_size)
        record = records[0]
        if record is None:
            continue
        sample_ids.append(record.sample_id)

    LOG.debug("Creating newick tree; checksums: %s; leaf names: %s", checksums, sample_ids)
    newick = tree_to_newick(node=tree, newick="", parentdist=tree.dist, leaf_names=sample_ids)
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
    matches = results["matches"]
    LOG.info("Found %d similar samples", len(matches))

    # if 1 or 0 samples were found, return empty newick
    if len(matches) < 2:
        LOG.warning("Invalid number of samples found, %d", len(matches))
        return "()"

    # load sequence signatures to memory
    repo = create_signature_repo()
    kmer_size = cnf.kmer_size
    sample_ids: list[str] = []
    for match in matches:
        sample_ids.append(match["sample_id"])
    signatures = _load_signatures_from_sample_id(sample_ids, kmer_size=kmer_size)

    if len(signatures) != len(sample_ids):
        raise ValueError("Could not load one signature for every similar sample")

    # cluster samples
    LOG.info("Cluster samples...")
    tree, _ = cluster_signatures(signatures, method)
    newick = tree_to_newick(tree, "", tree.dist, sample_ids)
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
