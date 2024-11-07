"""Functions for clustering using a distance matrix."""

import logging
from enum import Enum

import pandas as pd
from scipy.cluster import hierarchy

LOG = logging.getLogger(__name__)


class ClusterMethod(str, Enum):
    """Index of methods for hierarchical clustering of samples."""

    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"
    WEIGHTED = "weighted"
    CENTROID = "centroid"


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


def cluster_distances(distance_matrix: pd.DataFrame, method: ClusterMethod) -> str:
    """Cluster two or more samples from a distance matrix."""

    linkage = hierarchy.linkage(distance_matrix, method=method.value)
    tree = hierarchy.to_tree(linkage, False)

    # creae newick tree
    newick_tree = to_newick(tree, "", tree.dist, list(distance_matrix.columns))
    return newick_tree
