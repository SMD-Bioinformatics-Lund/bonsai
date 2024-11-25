"""Functions for building and merging indexes."""

import logging
import tempfile
from pathlib import Path
from typing import Sequence

from ..config import Settings
from .base import ska_base

LOG = logging.getLogger(__name__)


def resolve_index_path(
    file_name: str, cnf: Settings, find_missing: bool = False
) -> Path:
    """Resolve and check path to index file.

    If the index cant be found, it will optionally search the index_path directory
    for the file.
    """
    index_path = Path(cnf.index_dir) / file_name

    # if file exists
    if index_path.is_file():
        return index_path

    # else try to find the file
    if find_missing:
        LOG.info("Trying to find file %s by recursive search", file_name)
        for root, _, files in Path(cnf.index_dir).walk():
            if index_path.name in files:
                return Path(root) / index_path.name

    # if file cannot be found in index_dir raise error
    raise FileNotFoundError(file_name)


def ska_merge(index_files: Sequence[Path], output: Path | None = None) -> Path:
    """
    Merge one or more index files with an optional output.

    Returns path to the output file.

    reference: https://docs.rs/ska/latest/ska/#ska-merge
    """
    # verify input files.
    if len(index_files) == 0:
        raise ValueError("You must provide one or more index files as input.")
    # sanity check that file exists.
    for file in index_files:
        if not isinstance(file, Path):
            raise ValueError(f"Input is not a {repr(Path)} object.")
        if not file.is_file():
            raise FileNotFoundError(f"Path {file} is not valid.")

    # verify type of output file.
    if not isinstance(output, Path | None):
        raise ValueError(f"Output path is not a {repr(Path)}")

    # create temporary directory if no inputfile was generated
    output = output if output is not None else Path(tempfile.mkstemp(suffix=".skf")[1])

    LOG.info("Merging files %s into %s", index_files, output)
    # merge index files
    ska_base("merge", arguments=index_files, options={"o": output})
    return output
