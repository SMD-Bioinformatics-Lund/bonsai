"""Read and write sourmash signature files."""

import logging
from pathlib import Path
from typing import Iterable, cast

import sourmash
from sourmash.signature import FrozenSourmashSignature

from minhash_service.core.exceptions import SignatureNotFoundError

from .models import SourmashSignatures

LOG = logging.getLogger(__name__)


def read_signatures(path: Path, kmer_size: int | None = None) -> SourmashSignatures:
    """Read signature to memory."""
    # read signature
    loaded = cast(
        Iterable[FrozenSourmashSignature],
        sourmash.load_file_as_signatures(str(path), ksize=kmer_size),
    )

    # check that were signatures loaded with current kmer
    loaded_sigs: SourmashSignatures = list(loaded)
    if len(loaded_sigs) == 0:
        raise SignatureNotFoundError(
            f"No signatures with ksize: {kmer_size} for file {path}"
        )
    return loaded_sigs


def write_signatures(
    path: Path,
    signature: str,
    kmer_size: int | None = None,
    name: str | None = None,
) -> Path:
    """
    Write signature to PATH.

    Optionally
    - only include signature of KMER size
    - rename signatrue to name
    """
    # convert signature from JSON to a mutable signature object
    # then annotate sample_id as name
    loaded_signatures = cast(
        Iterable[FrozenSourmashSignature],
        sourmash.signature.load_signatures_from_json(signature, ksize=kmer_size),
    )
    upd_signatures: list[FrozenSourmashSignature] = []
    for sig_obj in loaded_signatures:
        if name is not None:
            sig_obj = sig_obj.to_mutable()
            sig_obj.name = name  # assign sample id as name
            sig_obj = cast(FrozenSourmashSignature, sig_obj.to_frozen())
        upd_signatures.append(sig_obj)
    LOG.info("Loaded %d signatures to memory", len(upd_signatures))

    # save signature to file
    LOG.info("Write signature file to %s", path)
    try:
        with open(path, "w", encoding="utf-8") as out:
            sourmash.signature.save_signatures_to_json(upd_signatures, out)
    except PermissionError:
        LOG.error("Dont have permission to write file to disk, %s", path)
        raise

    return path
