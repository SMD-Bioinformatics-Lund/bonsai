"""Function for clustering."""
from scipy.cluster import hierarchy
from scipy.spatial.distance import pdist
from ..crud.sample import TypingProfileOutput
from enum import Enum
import pandas as pd
from skbio.tree import nj
from skbio import DistanceMatrix


class DistanceMethod(Enum):
    """Index of methods for calculating the distance matrix during hierarchical clustering of samples."""

    JACCARD = "jaccard"
    HAMMING = "hamming"


class ClusterMethod(Enum):
    """Index of methods for hierarchical clustering of samples."""

    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"
    NJ = "neighbor_joining"


def to_newick(node, newick, parentdist, leaf_names):
    """Convert hierarcical tree representation to newick format."""

    if node.is_leaf():
        return "%s:%.2f%s" % (leaf_names[node.id], parentdist - node.dist, newick)
    else:
        if len(newick) > 0:
            newick = "):%.2f%s" % (parentdist - node.dist, newick)
        else:
            newick = ");"
        newick = to_newick(node.get_left(), newick, node.dist, leaf_names)
        newick = to_newick(node.get_right(), f",{newick}", node.dist, leaf_names)
        newick = f"({newick}"
        return newick


def cluster_on_allele_profile(
    profiles: TypingProfileOutput,
    method: ClusterMethod,
    distance_metric: DistanceMethod,
) -> str:
    """Cluster samples on allele profiles."""
    obs = pd.DataFrame(
        [s.typingResult for s in profiles], index=[s.sampleId for s in profiles]
    )
    leaf_names = list(obs.index)
    # calcualte distance matrix
    raise ValueError(profiles)
    dist_mtrx = pdist(obs, metric=distance_metric.value)

    if method == ClusterMethod.NJ:
        dm = DistanceMatrix(dist_mtrx, leaf_names)
        newick_tree = nj(dm, result_constructor=str)
    else:
        # to use the clustering methods in scipy
        Z = hierarchy.linkage(dist_mtrx, method=method.value)
        # convert distance matrix to cluster
        tree = hierarchy.to_tree(Z, False)
        newick_tree = to_newick(tree, "", tree.dist, leaf_names)
    return newick_tree
