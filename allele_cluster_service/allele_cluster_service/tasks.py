"""Define reddis tasks."""
import logging

from .ms_trees import ClusterMethod, backend

LOG = logging.getLogger(__name__)


def cluster(profile: str, method: str) -> str:
    """
    Cluster multiple sample on their allele profiles.

    :param profile str: a string representation of a tsv table of the allele profiles
    :param method str: the MStree clustering method

    :raises ValueError: raises an exception if the method is not a valid MSTree clustering method.

    :return: cluster in newick format
    :rtype: str
    """
    try:
        method = ClusterMethod(method)
    except ValueError:
        msg = f'"{method}" is not a valid cluster method'
        LOG.error(msg)
        raise ValueError(msg)
    newick = backend(profile=profile, method=method.value)
    return newick
