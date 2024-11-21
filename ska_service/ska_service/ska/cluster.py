"""Functions for clustering using a distance matrix."""

import logging
from enum import Enum
from typing import Sequence

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


def cluster_distances(distance_matrix: pd.DataFrame, method: ClusterMethod) -> str:
    """Cluster two or more samples from a distance matrix."""

    linkage = hierarchy.linkage(distance_matrix, method=method.value)
    tree = hierarchy.to_tree(linkage, False)

    newick_tree = to_newick(tree, "", tree.dist, list(distance_matrix.columns))
    return newick_tree
