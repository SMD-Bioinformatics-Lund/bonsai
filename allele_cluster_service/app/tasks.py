"""Define reddis tasks."""
import logging

from .ms_trees import ClusterMethod, backend

LOG = logging.getLogger(__name__)


def cluster(profile: str, method: str) -> str:
    """Cluster multiple sample on their allele signatures."""
    try:
        method = ClusterMethod(method)
    except ValueError:
        msg = f'"{method}" is not a valid cluster method'
        LOG.error(msg)
        raise ValueError(msg)
    # cluster
    # "matrix_type": asymmetric or symmetric
    # "heuristic": harmonic or eBurst
    # "branch_recraft": T or F
    newick = backend(profile=profile, method=method.value)
    return newick
