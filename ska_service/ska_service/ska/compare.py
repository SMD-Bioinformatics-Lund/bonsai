"""Calculate SNV distance from index files."""

import itertools
import tempfile
from pathlib import Path

import pandas as pd

from .base import ska_base


def _to_dist_matrix(dist_df: pd.DataFrame) -> pd.DataFrame:
    """Convert SKA distance output to symetric distance matrix."""
    # get all samples in matrix
    samples = pd.concat([dist_df.Sample1, dist_df.Sample2]).unique()

    # index output to support matrix creation
    dist_df.set_index(["Sample1", "Sample2"], inplace=True)

    # create distance matrix
    dist_matrix = pd.DataFrame(index=samples, columns=samples).fillna(1)
    for first, second in itertools.combinations(samples, 2):
        # upper
        dist_matrix.loc[first, second] = dist_df.loc[(first, second), "Distance"]
        # lower
        dist_matrix.loc[second, first] = dist_df.loc[(first, second), "Distance"]
    return dist_matrix


def ska_distance(
    index_file: Path, threads: int = 1, dist_matrix: bool = False
) -> pd.DataFrame:
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
        return _to_dist_matrix(dist_df)
    return dist_df
