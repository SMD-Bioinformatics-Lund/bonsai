"""Define reddis tasks."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Sequence

from Bio import AlignIO

from . import ska
from .config import settings
from .ska.cluster import ClusterMethod, calc_snv_distance, to_newick

LOG = logging.getLogger(__name__)


def get_index_name(index_path: str) -> str:
    """Get the name of the index from the file path."""
    return Path(index_path).stem.replace('_ska_index', '')


def cluster(indexes: Sequence[dict[str, str]], cluster_method: str = "single") -> str:
    """
    Cluster multiple sample on their SNVs using SKA indexes.

    :param indexes List[str]: Paths to one or more SKA indexes.
    :param cluster_method str: The linkage or clustering method to use, default to single

    :raises ValueError: raises an exception if the method is not a valid scipy clustering method.

    :return: clustering result in newick format
    :rtype: str
    """
    # validate input samples and cast to path
    idx_paths = [Path(settings.index_dir) / idx["ska_index"] for idx in indexes]

    sample_id_lookup = {
        get_index_name(idx["ska_index"]): idx["sample_id"] 
        for idx in indexes
    }

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

        # align variants and return as multi fasta
        aln_file = ska.align(merged_index, filter_ambig=True, filter_constant=True)

        # calculate distance between samples from alignment and cluster
        with open(aln_file) as inpt:
            aln = AlignIO.read(inpt, "fasta")
        dm = calc_snv_distance(aln)
        tree, index_names = ska.cluster_distances(dm, method)
        # lookup sample ids from index names and return newick tree with sample ids as leaf names
        sample_ids = [sample_id_lookup.get(idx, idx) for idx in index_names]
        newick_tree = to_newick(tree, "", tree.dist, sample_ids)
    return newick_tree


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
