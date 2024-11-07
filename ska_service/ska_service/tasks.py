"""Define reddis tasks."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Sequence

from . import ska
from .ska.cluster import ClusterMethod

LOG = logging.getLogger(__name__)


def cluster(indexes: Sequence[str], cluster_method: str = "single") -> str:
    """
    Cluster multiple sample on their SNVs using SKA indexes.

    :param indexes List[str]: Paths to one or more SKA indexes.
    :param cluster_method str: The linkage or clustering method to use, default to single

    :raises ValueError: raises an exception if the method is not a valid scipy clustering method.

    :return: clustering result in newick format
    :rtype: str
    """
    # validate input samples and cast to path
    idx_paths = [Path(idx) for idx in indexes]

    # validate cluster method
    try:
        method = ClusterMethod(cluster_method)
    except ValueError as error:
        msg = f'"{cluster_method}" is not a valid cluster method'
        LOG.error(msg)
        raise ValueError(msg) from error

    with TemporaryDirectory() as tmp_dir:
        # merge indexes into a single file
        merged_index = ska.merge(idx_paths, output=Path(tmp_dir).joinpath("merged.skf"))
        # get SNV distance between samples
        dist = ska.distance(merged_index, dist_matrix=True)
        nwk = ska.cluster_distances(dist, method)
    return nwk
