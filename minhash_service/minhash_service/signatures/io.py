"""Read and write sourmash signature files."""

from pathlib import Path

import sourmash

from minhash_service.core.config import Settings

from .models import SourmashSignatures


def read_signature(path: Path, cnf: Settings) -> SourmashSignatures:
    """Read signature to memory."""
    # read signature
    loaded = sourmash.load_file_as_signatures(str(path), ksize=cnf.kmer_size)

    # check that were signatures loaded with current kmer
    loaded_sigs: SourmashSignatures = list(loaded)
    if len(loaded_sigs) == 0:
        raise ValueError(f"No signatures with ksize: {cnf.kmer_size} for file {path}")
    return loaded_sigs
