"""Define reddis tasks."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Sequence

from Bio import AlignIO
from bonsai_libs.clustering import LinkageMethod, ClusteringAlgorithm

from . import ska
from .config import settings

LOG = logging.getLogger(__name__)


def _parse_cluster_algorithm(algorithm: str) -> ClusteringAlgorithm:
    """Parse cluster algorithm."""

    try:
        return ClusteringAlgorithm(algorithm)
    except ValueError as error:
        LOG.error(
            "cluster.invalid_algorithm",
            extra={"algorithm": algorithm},
        )
        raise ValueError(f'"{algorithm}" is not a valid cluster algorithm') from error


def _parse_linkage_method(method: str) -> LinkageMethod:
    """Parse linkate method."""

    try:
        return LinkageMethod(method)
    except ValueError as error:
        LOG.error(
            "cluster.invalid_method",
            extra={"cluster_method": method},
        )
        raise ValueError(f'"{method}" is not a valid cluster method') from error


def get_index_name(index_path: str) -> str:
    """Get the name of the index from the file path."""
    return Path(index_path).stem.replace('_ska_index', '')


def cluster(
        indexes: Sequence[dict[str, str]], 
        cluster_method: str = "single",
        algorithm: str = "hierarchical",
    ) -> str:
    """
    Cluster samples using SKA indexes and return Newick tree.
    """

    # validate input samples and cast to path
    idx_paths = [Path(settings.index_dir) / idx["ska_index"] for idx in indexes]

    # Map index name → sample_id
    sample_id_lookup = {
        get_index_name(idx["ska_index"]): idx["sample_id"] 
        for idx in indexes
    }

    # Validate clustering algorithm and method (only needed for hierarchical)
    algorithm = _parse_cluster_algorithm(algorithm)
    method = _parse_linkage_method(cluster_method) if cluster_method else None

    # Core pipeline
    with TemporaryDirectory() as tmp_dir:
        merged_index = ska.merge(
            idx_paths,
            output=Path(tmp_dir) / "merged.skf",
        )

        aln_file = ska.align(
            merged_index,
            filter_ambig=True,
            filter_constant=True,
        )

        with open(aln_file, encoding="utf-8") as handle:
            aln = AlignIO.read(handle, "fasta")

    # Map names after alignment
    sample_ids = [
        sample_id_lookup.get(name, name)
        for name in (aln_i.name for aln_i in aln)
    ]

    return ska.cluster_alignment(
        aln,
        sample_ids,
        algorithm=algorithm,
        method=method,
    )


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
