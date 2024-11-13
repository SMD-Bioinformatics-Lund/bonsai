"""Define reddis tasks."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Sequence, Dict

from . import ska
from .ska.cluster import ClusterMethod

from .config import settings

LOG = logging.getLogger(__name__)


def cluster(indexes: Sequence[Dict[str, str]], cluster_method: str = "single") -> str:
    """
    Cluster multiple sample on their SNVs using SKA indexes.

    :param indexes List[str]: Paths to one or more SKA indexes.
    :param cluster_method str: The linkage or clustering method to use, default to single

    :raises ValueError: raises an exception if the method is not a valid scipy clustering method.

    :return: clustering result in newick format
    :rtype: str
    """
    # validate input samples and cast to path
    idx_paths = [
        Path(settings.index_dir) / idx["ska_index"]
        for idx in indexes
    ]

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


def check_index(file_name: str) -> str | None:
    """Check if index exist and are accessable.

    returns true if the index file exists and are accessable, else false
    """
    LOG.info("Check if index file %s is accessable.", file_name)
    try:
        path: Path = ska.resolve_index_path(file_name, settings, find_missing=True)
        return str(path)
    except FileNotFoundError:
        LOG.error("The index file %s could not be found.", file_name)
    return None
