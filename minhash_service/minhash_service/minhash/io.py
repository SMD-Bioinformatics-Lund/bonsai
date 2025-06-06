"""Functions for reading and writing signatures"""

import gzip
import logging
import pathlib
from typing import Iterable

import fasteners
import sourmash
from sourmash.signature import FrozenSourmashSignature, SourmashSignature

from minhash_service.config import Settings

from .models import SignatureFile, SignatureName

LOG = logging.getLogger(__name__)
Signatures = list[SourmashSignature | FrozenSourmashSignature]


def get_sbt_index(cnf: Settings, check: bool = True) -> pathlib.Path:
    """Get sourmash SBT index file."""
    index_path = cnf.signature_dir.joinpath(f"{cnf.index_name}.sbt.zip")

    # Check if file exist
    if check:
        if not index_path.is_file():
            raise FileNotFoundError(f"Sourmash index does not exist: {index_path}")
    # Load index to memory
    return index_path


def get_signature_path(
    sample_id: str, signature_dir: pathlib.Path, check: bool = True
) -> str:
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


def read_signature(sample_id: str, cnf: Settings) -> Signatures:
    """Read signature to memory."""
    # read signature
    signature_path = get_signature_path(sample_id, signature_dir=cnf.signature_dir)
    loaded = sourmash.load_file_as_signatures(signature_path, ksize=cnf.kmer_size)

    # check that were signatures loaded with current kmer
    loaded_sigs = list(loaded)
    if len(loaded_sigs) == 0:
        raise ValueError(
            f"No signatures, sample id: {sample_id}, ksize: {cnf.kmer_size}, {loaded}"
        )
    return loaded_sigs


def write_signature(
    sample_id: str, signature: SignatureFile, cnf: Settings
) -> pathlib.Path:
    """
    Add genome signature to index.

    Create new index if none exist.
    """
    # get signature directory
    LOG.info("Adding signature file for %s", sample_id)
    signature_db = pathlib.Path(cnf.signature_dir)
    # make db if signature db is not present
    if not signature_db.exists():
        signature_db.mkdir(parents=True, exist_ok=True)

    # Get signature path and check if it exists
    signature_file = get_signature_path(
        sample_id, signature_dir=cnf.signature_dir, check=False
    )

    # check if compressed and decompress data
    LOG.info("Check if signature is compressed")
    if signature[:2] == b"\x1f\x8b":
        LOG.debug("Decompressing gziped file")
        signature = gzip.decompress(signature)

    # convert signature from JSON to a mutable signature object
    # then annotate sample_id as name
    signatures: Iterable[FrozenSourmashSignature] = sourmash.signature.load_signatures_from_json(
        signature, ksize=cnf.kmer_size
    )
    upd_signatures = []
    for sig_obj in signatures:
        sig_obj = sig_obj.to_mutable()
        sig_obj.name = sample_id  # assign sample id as name
        sig_obj.filename = pathlib.Path(signature_file).name  # assign a new filename
        sig_obj = sig_obj.to_frozen()
        upd_signatures.append(sig_obj)

    # save signature to file
    LOG.info("Writing genome signatures to file")
    try:
        with open(signature_file, "w", encoding="utf-8") as out:
            sourmash.signature.save_signatures_to_json(upd_signatures, out)
    except PermissionError as error:
        msg = f"Dont have permission to write file to disk, {signature_file}"
        LOG.error(msg)
        raise PermissionError(msg) from error

    return signature_file


def remove_signature(sample_id: str, cnf: Settings) -> bool:
    """Remove an existing signature file from disk."""
    # check that signature doesnt exist
    # Get signature path and check if it exists
    signature_file = get_signature_path(sample_id, signature_dir=cnf.signature_dir)

    # read signature
    next(sourmash.signature.load_signatures_from_json(signature_file, ksize=cnf.kmer_size))

    # remove file
    pathlib.Path(signature_file).unlink()
    LOG.info("Signature file: %s was removed", signature_file)
    return False


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


def add_signatures_to_index(sample_ids: list[str], cnf: Settings) -> bool:
    """Add genome signature file to sourmash index"""

    genome_index = get_sbt_index(cnf=cnf, check=False)
    sbt_lock_path = f"/tmp/{genome_index.name}.lock"
    lock = fasteners.InterProcessLock(sbt_lock_path)
    LOG.debug("Using lock: %s", sbt_lock_path)

    signatures = []
    for sample_id in sample_ids:
        signature = read_signature(sample_id, cnf)
        signatures.append(signature[0])

    # add signature to existing index
    # acquire lock to append signatures to database
    LOG.debug("Attempt to acquire lock to append %s to index...", signatures)
    with lock:
        # check if index already exist
        try:
            index_path = get_sbt_index(cnf=cnf)
            tree = sourmash.load_file_as_index(str(index_path))
        except ValueError as error:
            LOG.warning("Error when reading index, %s; creating new index", error)
            tree = sourmash.sbtmh.create_sbt_index()
        except FileNotFoundError:
            tree = sourmash.sbtmh.create_sbt_index()

        # add generated signature to bloom tree
        LOG.info("Adding %d genome signatures to index", len(signatures))
        for signature in signatures:
            leaf = sourmash.sbtmh.SigLeaf(signature.md5sum(), signature)
            tree.add_node(leaf)
        # save updated bloom tree
        try:
            index_path = get_sbt_index(cnf=cnf, check=False)
            tree.save(str(index_path))
        except PermissionError as err:
            LOG.error("Dont have permission to write file to disk")
            raise err

    return True


def remove_signatures_from_index(sample_ids: list[str], cnf: Settings) -> bool:
    """Add genome signature file to sourmash index"""

    genome_index = get_sbt_index(cnf=cnf, check=False)
    sbt_lock_path = f"{genome_index.name}.lock"
    lock = fasteners.InterProcessLock(sbt_lock_path)
    LOG.debug("Using lock: %s", sbt_lock_path)

    # remove signature from existing index
    # acquire lock to remove signatures from database
    LOG.debug("Attempt to acquire lock to append %s to index...", sample_ids)
    with lock:
        # check if index already exist
        index_path = get_sbt_index(cnf)
        old_index = sourmash.load_file_as_index(str(index_path))

        # add signatures not among the sample ids a new index
        LOG.info("Removing %d genome signatures to index", len(sample_ids))
        new_index = sourmash.sbtmh.create_sbt_index()
        for signature in old_index.signatures():
            sample_id = signature.name
            if sample_id not in sample_ids:
                leaf = sourmash.sbtmh.SigLeaf(signature.md5sum(), signature)
                new_index.add_node(leaf)

        # save new bloom tree
        try:
            index_path = get_sbt_index(cnf, check=False)
            new_index.save(str(index_path))
        except PermissionError as err:
            LOG.error("Dont have permission to write file to disk")
            raise err

    return True


def list_signatures_in_index(cnf: Settings) -> list[SignatureName]:
    """List signatures in index."""

    index_path = get_sbt_index(cnf=cnf, check=False)
    idx = sourmash.load_file_as_index(str(index_path))
    return [
        SignatureName.model_validate({"name": sig.name, "filename": sig.filename})
        for sig in idx.signatures()
    ]
