"""Functions for reading and writing signatures"""

import logging
from pathlib import Path

import sourmash
from sourmash.signature import FrozenSourmashSignature, SourmashSignature

from minhash_service.core.config import Settings

LOG = logging.getLogger(__name__)
Signatures = list[SourmashSignature | FrozenSourmashSignature]


def get_sbt_index(cnf: Settings, check: bool = True) -> Path:
    """Get sourmash SBT index file."""
    index_path = cnf.signature_dir.joinpath(f"{cnf.index_name}.sbt.zip")

    # Check if file exist
    if check:
        if not index_path.is_file():
            raise FileNotFoundError(f"Sourmash index does not exist: {index_path}")
    # Load index to memory
    return index_path


def get_signature_path(sample_id: str, signature_dir: Path, check: bool = True) -> str:
    """
    Get path to a sample signature file.

    :param sample_id str: Sample id
    :param check bool: if it should check if file is present

    :return: path to the signature
    :rtype: str
    """
    signature_path = signature_dir.joinpath(f"{sample_id}.sig")

    # Check if file exist
    if check:
        if not signature_path.is_file():
            raise FileNotFoundError(f"Signature file not found, {signature_path}")
    # Load index to memory
    return str(signature_path)


def read_signature(path: Path, cnf: Settings) -> Signatures:
    """Read signature to memory."""
    # read signature
    loaded = sourmash.load_file_as_signatures(str(path), ksize=cnf.kmer_size)

    # check that were signatures loaded with current kmer
    loaded_sigs = list(loaded)
    if len(loaded_sigs) == 0:
        raise ValueError(f"No signatures with ksize: {cnf.kmer_size} for file {path}")
    return loaded_sigs


def check_signature(sample_id: str, cnf: Settings) -> bool:
    """Check if signature exist and has been added to the index."""
    LOG.info("Checking signature file: %s", signature_file)
    try:
        signature_file = get_signature_path(
            sample_id, signature_dir=cnf.signature_dir, check=True
        )
    except FileExistsError:
        return False
    else:
        return True
