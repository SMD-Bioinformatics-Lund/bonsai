"""Calculate SNV distance from index files."""

import itertools
import tempfile
from pathlib import Path

import pandas as pd

from .base import ska_base
from .cluster import DistanceMatrix


def _ska_dist_to_dist_matrix(dist_df: pd.DataFrame) -> DistanceMatrix:
    """Convert SKA distance output to symetric distance matrix."""
    # index output to support matrix creation
    dist_df.set_index(["Sample1", "Sample2"], inplace=True)

    # create distance matrix
    sample_names = pd.concat([dist_df.Sample1, dist_df.Sample2]).unique()
    dm = DistanceMatrix(names=sample_names)
    for seq1, seq2 in itertools.combinations(sample_names, 2):
        dm[seq1.name, seq2.name] = dist_df.loc[(seq1, seq2), "Distance"]
    return dm


def ska_distance(
    index_file: Path, threads: int = 1, dist_matrix: bool = False
) -> DistanceMatrix:
    """
    Calculate distances between all samples within an .skf file.

    reference: https://docs.rs/ska/latest/ska/#ska-distance
    """
    # sanity check that file exists.
    if not index_file.is_file():
        raise FileNotFoundError(index_file)

    # create temporary directory if no inputfile was generated
    output = Path(tempfile.mkstemp(suffix=".tsv")[1])

    # run command
    ska_base(
        "distance", arguments=[index_file], options={"o": output, "threads": threads}
    )

    # read output
    dist_df = pd.read_csv(
        output, sep="\t", dtype={"Distance": int, "Missmatches": float}
    )

    if dist_matrix:
        return _ska_dist_to_dist_matrix(dist_df)
    return dist_df


def ska_align(
    index_file: Path,
    threads: int = 1,
    filter_ambig: bool = False,
    filter_constant: bool = True,
) -> pd.DataFrame:
    """
    Calculate distances between all samples within an .skf file.

    reference: https://docs.rs/ska/latest/ska/#ska-distance
    """
    # sanity check that file exists.
    if not index_file.is_file():
        raise FileNotFoundError(index_file)

    # create temporary directory if no inputfile was generated
    output = Path(tempfile.mkstemp(suffix=".aln")[1])

    if filter_ambig and filter_constant:
        filter_opt = "no-ambig-or-const"
    elif filter_ambig and not filter_constant:
        filter_opt = "no-ambig"
    elif filter_constant and not filter_ambig:
        filter_opt = "no-const"
    else:
        filter_opt = "no-filter"

    # run command
    ska_base(
        "align",
        arguments=[index_file, "--no-gap-only-sites", "--filter-ambig-as-missing"],
        options={"o": output, "threads": threads, "filter": filter_opt},
    )
    return output
