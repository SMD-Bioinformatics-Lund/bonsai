"""Define reddis tasks."""
from typing import List, Dict
from pathlib import Path
from .minhash.cluster import cluster_signatures, ClusterMethod
from .minhash.io import write_signature, add_signatures_to_index
from .minhash.io import remove_signature as remove_signature_file
from .minhash.similarity import get_similar_signatures, SimilarSignatures

import logging

LOG = logging.getLogger(__name__)


def add_signature(sample_id: str, signature) -> str:
    """
    Find signatures similar to reference signature.

    Retun list of similar signatures that describe signature and similarity.
    """
    signature_path = write_signature(sample_id, signature)
    return str(signature_path)


def remove_signature(sample_id: str) -> Dict[str, str | bool]:
    """
    Find signatures similar to reference signature.

    Retun list of similar signatures that describe signature and similarity.
    """
    status: bool = remove_signature_file(sample_id)
    return {"sample_id": sample_id, "removed": status}


def index(signature_files: List[Path]):
    """Index sourmash signatures."""
    LOG.info("Indexing signatures...")
    res = add_signatures_to_index(signature_files)
    signatures = ", ".join([file.name for file in signature_files])
    if res:
        msg = f"Appended {signatures}"
    else:
        msg = f"Failed to append signatures, {signatures}"
    return msg


def similar(
    sample_id: str, min_similarity: float = 0.5, limit: int | None = None
) -> SimilarSignatures:
    """
    Find signatures similar to reference signature.

    Retun list of similar signatures that describe signature and similarity.
    """
    samples = get_similar_signatures(
        sample_id, min_similarity=min_similarity, limit=limit
    )
    LOG.info(
        f"Finding samples similar to {sample_id} with min similarity {min_similarity}; limit {limit}"
    )
    results = [s.model_dump() for s in samples]
    return results


def cluster(sample_ids: List[str], cluster_method: str = "single") -> str:
    """Cluster multiple sample on their sourmash signatures."""
    # validate input
    try:
        method = ClusterMethod(cluster_method)
    except ValueError:
        msg = f'"{cluster_method}" is not a valid cluster method'
        LOG.error(msg)
        raise ValueError(msg)
    # cluster
    newick: str = cluster_signatures(sample_ids, method)
    return newick


def find_similar_and_cluster(
    sample_id: str,
    min_similarity: float = 0.5,
    limit: int | None = None,
    cluster_method: str = "single",
) -> str:
    """Find similar samples and cluster them on their minhash profile."""
    # validate input
    try:
        method = ClusterMethod(cluster_method)
    except ValueError:
        msg = f'"{cluster_method}" is not a valid cluster method'
        LOG.error(msg)
        raise ValueError(msg)
    sample_ids = get_similar_signatures(
        sample_id, min_similarity=min_similarity, limit=limit
    )

    # if 1 or 0 samples were found, return emtpy newick
    if len(sample_ids) < 2:
        LOG.warning(f"{len(sample_ids)}")
        return "()"
    # cluster samples
    newick: str = cluster_signatures(sample_ids, method)
    return newick
