"""Define reddis tasks."""

import logging
import dataclasses
from typing import Any

import sourmash


from .config import settings
from .minhash.cluster import ClusterMethod, cluster_signatures
from .minhash.io import (
    save_signature_file, remove_signature_file, read_signature
)
from .minhash.models import SignatureFile, SimilarSignatures
from .minhash.paths import ensure_file_exists, get_index_path, get_signature_files, get_signature_path
from .minhash.similarity import get_similar_signatures
from .minhash.index import SourmashIndexStore

LOG = logging.getLogger(__name__)


def add_signature(sample_id: str, signature: SignatureFile) -> str:
    """
    Add a new signature to minhash service by saving it to disk and indexing it.

    :param sample_id str: the sample_id
    :param signature dict[str, str]: sourmash signature file in JSON format

    :return: path to the signature
    :rtype: str
    """
    signature_path = save_signature_file(sample_id, signature, cnf=settings)
    return str(signature_path)


def remove_signature(sample_id: str) -> dict[str, str | bool]:
    """
    Remove a signature from the database and index.

    :param sample_id str: the sample_id of the signature to remove

    :return: The status of the removed job
    :rtype: Dict[str, str | bool]
    """
    status: bool = remove_signature_file(sample_id)
    return {"sample_id": sample_id, "removed": status}


def check_signature(sample_id: str) -> dict[str, str | bool]:
    """Check if signature exist."""

    path = get_signature_path(sample_id, ensure_exists=False)
    try:
        ensure_file_exists(path)
        exists = True
    except FileNotFoundError:
        exists = False
    try:
        idx_path = get_index_path()
        idx = SourmashIndexStore(idx_path, settings.db_format)
        indexed_sigs = idx.list_signatures()
    except FileNotFoundError:
        LOG.warning("Index not found")

    return {"sample_id": sample_id, "path": path, "exists": exists, "indexed": sample_id in indexed_sigs}


def add_to_index(sample_ids: list[str]) -> str:
    """
    Add signatures to sourmash index.

    :param sample_ids list[str]: The path to multiple signature files

    :return: result message
    :rtype: str
    """
    # read index
    idx_path = get_index_path(ensure_exists=False)
    idx = SourmashIndexStore(idx_path, settings.db_format)

    LOG.info("Indexing %d signatures", len(sample_ids))
    signatures = []
    for s in sample_ids:
        path = get_signature_path(s)
        sig = read_signature(path, kmer_size=settings.kmer_size)
        signatures.extend(sig)

    res = idx.add_signatures(signatures)
    return dataclasses.asdict(res)


def remove_from_index(sample_ids: list[str]) -> str:
    """
    Remove signatures from sourmash SBT index.

    :param sample_ids list[str]: Sample ids of signatures to remove

    :return: result message
    :rtype: str
    """
    LOG.info("Removing samples %d from index.", len(sample_ids))
    # read index
    idx_path = get_index_path()
    idx = SourmashIndexStore(idx_path, settings.db_format)
    res = idx.remove_signatures_by_names(sample_ids)
    return dataclasses.asdict(res)


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
    samples = get_similar_signatures(
        sample_id, min_similarity=min_similarity, limit=limit, cnf=settings
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
    newick: str = cluster_signatures(sample_ids, method, cnf=settings)
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
    sample_ids = get_similar_signatures(
        sample_id, min_similarity=min_similarity, limit=limit, cnf=settings
    )

    # if 1 or 0 samples were found, return emtpy newick
    if len(sample_ids) < 2:
        LOG.warning("Invalid number of samples found, %d", len(sample_ids))
        return "()"
    sids = [sid.sample_id for sid in sample_ids]
    # cluster samples
    LOG.info(
        "Clustering the following samples to %s: ",
        ", ".join(sids),
    )
    newick: str = cluster_signatures(sids, method, cnf=settings)
    return newick


def reindex_database(drop_db: bool = False) -> dict[str, str | int]:
    """Reindex the database using all stored signature files."""

    sig_paths = get_signature_files(settings.signature_dir)
    LOG.info("Got job to reindex all samples %d", len(sig_paths))
    idx_path = get_index_path()
    # drop existing database
    if drop_db:
        idx_path.unlink()

    idx = SourmashIndexStore(idx_path, index_format=settings.db_format)
    sigs = [read_signature(path, settings.kmer_size) for path in sig_paths]
    res = idx.add_signatures(sigs)

    return {
        "index_format": settings.db_format, 
        "samples_count": len(sig_paths), 
        "indexed_count": res.added_count
    }


def info() -> dict[str, Any]:
    """Get information on sourmash installation and database."""

    index_path = get_index_path(ensure_exists=False)
    try:
        index_exists = ensure_file_exists(index_path)
    except FileNotFoundError:
        index_exists = False

    n_signatures: int = sum([1 for s in get_signature_files(settings.signature_dir)])

    return {
        "version": sourmash.VERSION,
        "kmer_size": settings.kmer_size,
        "index": {
            "path": str(index_path),
            "format": settings.db_format.name,
            "exists": index_exists,
        },
        "signatures": {"path": str(settings.signature_dir), "n_signatures": n_signatures},
    }
