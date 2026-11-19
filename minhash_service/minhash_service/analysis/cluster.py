"""Functions for clustering on minhashes"""

import logging
from typing import Any

import sourmash
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform

from minhash_service.signatures.models import SourmashSignatures

from .models import ClusterMethod

LOG = logging.getLogger(__name__)


def tree_to_newick(node, newick, parentdist, leaf_names) -> str:
    """Convert a hierarchical tree to Newick without rounding branch lengths."""

    branch_length = float(parentdist - node.dist)

    if node.is_leaf():
        return f"{leaf_names[node.id]}:{branch_length}{newick}"

    if len(newick) > 0:
        newick = f"):{branch_length}{newick}"
    else:
        newick = ");"
    newick = tree_to_newick(node.get_left(), newick, node.dist, leaf_names)
    newick = tree_to_newick(node.get_right(), f",{newick}", node.dist, leaf_names)
    newick = f"({newick}"
    return newick


def cluster_signatures(
    signatures: list[SourmashSignatures],
    method: ClusterMethod,
    ignore_abundance: bool = True,
) -> tuple[Any, list[str]]:
    """Cluster multiple samples on their minhash signatures and return tree object."""

    # Calculate pairwise similarities between signatures.
    similarity = sourmash.compare.compare_all_pairs(
        signatures, ignore_abundance=ignore_abundance, n_jobs=1, return_ani=False
    )
    # Input to hierachy.linkage is expected to be either a vector of distances or
    # 2-D array of observation vectors
    # See documentation: https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.linkage.html#scipy.cluster.hierarchy.linkage
    distances = squareform(1 - similarity)
    linkage = hierarchy.linkage(distances, method=method.value)
    tree = hierarchy.to_tree(linkage, False)
    checksums: list[str] = [sig.md5sum() for sig in signatures]
    return tree, checksums
