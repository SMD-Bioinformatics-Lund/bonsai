"""Functions for clustering on minhashes"""

import logging

import sourmash

from bonsai_libs.clustering import hierarchical_clustering, minimum_spanning_tree_clustering, LinkageMethod, ClusteringAlgorithm, ClusterResult
from minhash_service.signatures.models import SourmashSignatures

LOG = logging.getLogger(__name__)


def cluster_signatures(
    signatures: SourmashSignatures,
    *,
    algorithm: ClusteringAlgorithm = ClusteringAlgorithm.HIERARCHICAL,
    method: LinkageMethod | None = None,
    ignore_abundance: bool = True,
) -> tuple[ClusterResult, list[str]]:
    """
    Cluster minhash signatures and return Newick + checksum order.
    """

    similarity = sourmash.compare.compare_all_pairs(
        signatures,
        ignore_abundance=ignore_abundance,
        n_jobs=1,
        return_ani=False,
    )

    checksums = [sig.md5sum() for sig in signatures]

    if algorithm == ClusteringAlgorithm.HIERARCHICAL:
        method = method or LinkageMethod.SINGLE

        result = hierarchical_clustering(
            similarity,
            checksums,
            method=method,
        )

    elif algorithm == ClusteringAlgorithm.MST:
        result = minimum_spanning_tree_clustering(
            similarity,
            checksums,
        )

    else:
        raise ValueError(f"Unknown clustering algorithm: {algorithm}")

    return result, checksums
