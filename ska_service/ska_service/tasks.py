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


def cluster(indexes: Sequence[dict[str, str]], cluster_method: str = "single") -> str:
    """
    Cluster multiple sample on their SNVs using SKA indexes.

    :param indexes List[str]: Paths to one or more SKA indexes.
    :param cluster_method str: The linkage or clustering method to use, default to single

    :raises ValueError: raises an exception if the method is not a valid scipy clustering method.

    :return: clustering result in newick format
    :rtype: str
    """
    # Resolve indexes inside the worker's mounted data directory. Stored paths
    # may refer to their original host location, so also search by filename.
    idx_paths: list[Path] = []
    missing_samples: list[str] = []
    for index in indexes:
        try:
            idx_paths.append(
                ska.resolve_index_path(
                    index["ska_index"], settings, find_missing=True
                )
            )
        except FileNotFoundError:
            missing_samples.append(index.get("external_sample_id") or "Unknown sample")

    if missing_samples:
        sample_labels = ", ".join(sorted(missing_samples))
        raise FileNotFoundError(
            "No SKA index file is available for the following samples: "
            f"{sample_labels}"
        )

    # validate cluster method
    try:
        method = ClusterMethod(cluster_method)
    except ValueError as error:
        msg = f'"{cluster_method}" is not a valid cluster method'
        LOG.error(msg)
        raise ValueError(msg) from error

    for index, path in zip(indexes, idx_paths):
        if ska.sample_count(path) != 1:
            label = index.get("external_sample_id") or "Unknown sample"
            raise ValueError(
                f"Expected a SKA index containing exactly one sample for {label}."
            )

    with TemporaryDirectory() as tmp_dir:
        # merge indexes into a single file
        merged_index = ska.merge(idx_paths, output=Path(tmp_dir).joinpath("merged.skf"))

        # align variants and return as multi fasta
        aln_file = ska.align(merged_index, filter_ambig=True, filter_constant=True)

        # calculate distance between samples from alignment and cluster
        with open(aln_file) as inpt:
            aln = AlignIO.read(inpt, "fasta")
        if len(aln) != len(indexes):
            raise ValueError("SKA alignment must contain one sequence per selected sample.")
        # SKA merge appends samples in input-file order. Each file above has
        # exactly one sample, so filenames and FASTA labels need not be unique.
        for sequence, index in zip(aln, indexes):
            sequence.id = sequence.name = index["sample_id"]
            sequence.description = ""
        dm = calc_snv_distance(aln)
        tree, sample_ids = ska.cluster_distances(dm, method)
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
