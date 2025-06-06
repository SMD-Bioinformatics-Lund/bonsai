"""Functions for clustering on minhashes"""
import logging
from enum import Enum
from typing import List

import sourmash
from scipy.cluster import hierarchy

from .io import read_signature
from minhash_service.config import Settings

LOG = logging.getLogger(__name__)


class ClusterMethod(str, Enum):
    """Index of methods for hierarchical clustering of samples."""

    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"


def to_newick(node, newick, parentdist, leaf_names) -> str:
    """Convert hierarcical tree representation to newick format."""

    if node.is_leaf():
        return f"{leaf_names[node.id]}:{parentdist - node.dist:.2f}{newick}"

    if len(newick) > 0:
        newick = f"):{parentdist - node.dist:.2f}{newick}"
    else:
        newick = ");"
    newick = to_newick(node.get_left(), newick, node.dist, leaf_names)
    newick = to_newick(node.get_right(), f",{newick}", node.dist, leaf_names)
    newick = f"({newick}"
    return newick


def cluster_signatures(sample_ids: List[str], method: ClusterMethod, cnf: Settings):
    """Cluster multiple samples on their minhash signatures."""

    # load sequence signatures to memory
    siglist = []
    LOG.info("Cluster signatures with sample ids: %s", sample_ids)
    for sample_id in sample_ids:
        signature = read_signature(sample_id, cnf=cnf)
        siglist.extend(signature)  # append to all signatures

    # create distance matrix
    similarity = sourmash.compare.compare_all_pairs(
        siglist, ignore_abundance=True, n_jobs=1, return_ani=False
    )
    # cluster on similarity matrix
    linkage = hierarchy.linkage(similarity, method=method.value)
    tree = hierarchy.to_tree(linkage, False)
    # creae newick tree
    labeltext = [str(item).replace(".fasta", "") for item in siglist]
    newick_tree = to_newick(tree, "", tree.dist, labeltext)
    return newick_tree
