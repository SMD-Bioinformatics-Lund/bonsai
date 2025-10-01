"""Functions for clustering on minhashes"""

import logging
from typing import Any

import sourmash
from scipy.cluster import hierarchy

from minhash_service.signatures.models import SourmashSignatures

from .models import ClusterMethod

LOG = logging.getLogger(__name__)


def tree_to_newick(node, newick, parentdist, leaf_names) -> str:
    """Convert hierarcical tree representation to newick format."""

    if node.is_leaf():
        return f"{leaf_names[node.id]}:{parentdist - node.dist:.2f}{newick}"

    if len(newick) > 0:
        newick = f"):{parentdist - node.dist:.2f}{newick}"
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

    # create distance matrix
    similarity = sourmash.compare.compare_all_pairs(
        signatures, ignore_abundance=ignore_abundance, n_jobs=1, return_ani=False
    )
    # cluster on similarity matrix
    linkage = hierarchy.linkage(similarity, method=method.value)
    tree = hierarchy.to_tree(linkage, False)
    checksums: list[str] = [sig.md5sum() for sig in signatures]
    return tree, checksums
