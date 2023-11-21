"""Define reddis tasks."""
import logging
from typing import Dict, List

from .minhash.cluster import ClusterMethod, cluster_signatures
from .minhash.io import add_signatures_to_index
from .minhash.io import remove_signature as remove_signature_file
from .minhash.io import write_signature
from .minhash.similarity import SimilarSignatures, get_similar_signatures

LOG = logging.getLogger(__name__)


def add_signature(sample_id: str, signature) -> str:
    """
    Find signatures similar to reference signature.

    :param sample_id str: the sample_id
    :param signature Dict[str, str]: sourmash signature file in JSON format

    :return: path to the signature
    :rtype: str
    """
    signature_path = write_signature(sample_id, signature)
    return str(signature_path)


def remove_signature(sample_id: str) -> Dict[str, str | bool]:
    """
    Remove a signature from the database and index.

    :param sample_id str: the sample_id of the signature to remove

    :return: The status of the removed job
    :rtype: Dict[str, str | bool]
    """
    status: bool = remove_signature_file(sample_id)
    return {"sample_id": sample_id, "removed": status}


def index(sample_ids: List[str]) -> str:
    """
    Add signatures to sourmash SBT index.

    :param sample_ids List[str]: The path to multiple signature files

    :return: result message
    :rtype: str
    """
    LOG.info("Indexing signatures...")
    res = add_signatures_to_index(sample_ids)
    signatures = ", ".join(list(sample_ids))
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

    :param sample_id str: The id of reference sample
    :param min_similarity float: Minimum similarity score
    :param limit int | None: Limit the result to x samples, default to None

    :return: list of the similar signatures
    :rtype: SimilarSignatures
    """
    samples = get_similar_signatures(
        sample_id, min_similarity=min_similarity, limit=limit
    )
    LOG.info(
        "Finding samples similar to %s with min similarity %s; limit %s",
        sample_id,
        min_similarity,
        limit,
    )
    results = [s.model_dump() for s in samples]
    return results


def cluster(sample_ids: List[str], cluster_method: str = "single") -> str:
    """
    Cluster multiple sample on their sourmash signatures.

    :param sample_ids List[str]: The sample ids to cluster
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
    newick: str = cluster_signatures(sample_ids, method)
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
    sample_ids = get_similar_signatures(
        sample_id, min_similarity=min_similarity, limit=limit
    )

    # if 1 or 0 samples were found, return emtpy newick
    if len(sample_ids) < 2:
        LOG.warning("Invalid number of samples found, %d", len(sample_ids))
        return "()"
    # cluster samples
    newick: str = cluster_signatures([sid.sample_id for sid in sample_ids], method)
    return newick
