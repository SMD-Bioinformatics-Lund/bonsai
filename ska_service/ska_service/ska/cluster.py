"""Functions for clustering using a distance matrix."""

import logging
from enum import Enum
import itertools
from typing import Sequence

from Bio.Align import MultipleSeqAlignment
from Bio.Phylo.TreeConstruction import DistanceMatrix as BioDistanceMatrix
from scipy.cluster import hierarchy

LOG = logging.getLogger(__name__)


class DistanceMatrix(BioDistanceMatrix):
    """Extended version of the DistanceMatrix from Biopython."""

    def to_condensed(self) -> Sequence[float | int]:
        """Convert to condensed distance matrix compatible with scipy linkage."""
        return [self.__getitem__((seq1, seq2)) for seq1, seq2 in itertools.combinations(self.names, 2)]


class ClusterMethod(str, Enum):
    """Index of methods for hierarchical clustering of samples."""

    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"
    WEIGHTED = "weighted"
    CENTROID = "centroid"


def to_newick(node: hierarchy.ClusterNode, newick: str, parent_dist: float, leaf_names: Sequence[str]) -> str:
    """Convert hierarcical tree representation to newick format."""

    if node.is_leaf():
        return f"{leaf_names[node.id]}:{parent_dist - node.dist:.2f}{newick}"

    if len(newick) > 0:
        newick = f"):{parent_dist - node.dist:.2f}{newick}"
    else:
        newick = ");"
    newick = to_newick(node.get_left(), newick, node.dist, leaf_names)
    newick = to_newick(node.get_right(), f",{newick}", node.dist, leaf_names)
    newick = f"({newick}"
    return newick


def calc_snv_distance(aln: MultipleSeqAlignment) -> DistanceMatrix:
    """Calculate pair-wise sample distance from aligned fasta sequences."""
    dm = DistanceMatrix(names=[al.name for al in aln])
    for seq1, seq2 in itertools.combinations(aln, 2):
        n_missing = sum(a_seq != b_seq for a_seq, b_seq in zip(seq1, seq2) if not any([a_seq == '-', b_seq == '-']))
        dm[seq1.name, seq2.name] = n_missing
    return dm


def cluster_distances(dm: DistanceMatrix, method: ClusterMethod) -> str:
    """Cluster two or more samples from a distance matrix."""

    linkage = hierarchy.linkage(dm.to_condensed(), method=method.value)
    tree = hierarchy.to_tree(linkage, False)

    newick_tree = to_newick(tree, "", tree.dist, dm.names)
    return newick_tree
