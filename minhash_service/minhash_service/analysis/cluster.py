"""Functions for clustering on minhashes"""

import logging
from enum import Enum
from pathlib import Path

import sourmash
from scipy.cluster import hierarchy

from minhash_service.core.config import Settings
from minhash_service.signatures.io import read_signatures
from minhash_service.signatures.models import SourmashSignatures

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


def cluster_signatures(
    signature_files: list[Path], method: ClusterMethod, cnf: Settings
):
    """Cluster multiple samples on their minhash signatures."""

    # load sequence signatures to memory
    siglist: SourmashSignatures = []
    LOG.info("Cluster %d signatures", len(signature_files))
    for sig_file in signature_files:
        signature = read_signatures(sig_file, kmer_size=cnf.kmer_size)
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
