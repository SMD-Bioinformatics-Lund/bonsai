"""Read and write sourmash signature files."""

import logging
from pathlib import Path
from typing import Iterable, cast

import sourmash
from sourmash.signature import FrozenSourmashSignature

from minhash_service.core.config import Settings
from minhash_service.core.exceptions import SignatureNotFoundError

from .index import BaseIndexStore
from .models import SignatureJSON, SourmashSignatures


LOG = logging.getLogger(__name__)


def read_signature(path: Path, kmer_size: int | None = None) -> SourmashSignatures:
    """Read signature to memory."""
    # read signature
    loaded = cast(
        Iterable[FrozenSourmashSignature],
        sourmash.load_file_as_signatures(str(path), ksize=kmer_size))

    # check that were signatures loaded with current kmer
    loaded_sigs: SourmashSignatures = list(loaded)
    if len(loaded_sigs) == 0:
        raise SignatureNotFoundError(f"No signatures with ksize: {kmer_size} for file {path}")
    return loaded_sigs


def write_signature(path: Path, signature: SignatureJSON, kmer_size: int | None = None, name: str | None = None) -> Path:
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
        sourmash.signature.load_signatures_from_json(signature, ksize=kmer_size)
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


def add_signatures_to_index_v2(signature_files: list[Path], index: BaseIndexStore):
    """Append genome signature files to provided sourmash index.

    Returns:
        tuple[bool, list[str]]: (success status, list of warning messages)
    """
    for sig_path in signature_files:


def add_signatures_to_index(
    signature_files: list[Path], cnf: Settings
) -> tuple[bool, list[str], list[str]]:
    """Append genome signature files to sourmash index.

    Returns:
        tuple[bool, list[str]]: (success status, list of warning messages)
    """

    genome_index = get_sbt_index(cnf=cnf, check=False)
    sbt_lock_path = f"/tmp/{genome_index.name}.lock"
    lock = fasteners.InterProcessLock(sbt_lock_path)
    LOG.debug("Using lock: %s", sbt_lock_path)

    warnings = []
    signatures = []
    for sig_path in signature_files:
        signature = read_signature(sig_path, cnf)
        if not signature:
            warning_msg = f"No relevant signatures in file {sig_path}"
            LOG.warning(warning_msg)
            warnings.append(warning_msg)
            continue
        signatures.append(signature[0])

    if not signatures:
        warning_msg = "No signatures to add."
        LOG.warning(warning_msg)
        warnings.append(warning_msg)
        return False, [], warnings

    # add signature to existing index
    # acquire lock to append signatures to database
    LOG.debug("Attempt to acquire lock to append %s to index...", signatures)
    with lock:
        # check if index already exist
        try:
            index_path = get_sbt_index(cnf=cnf)
            tree = sourmash.load_file_as_index(str(index_path))
            LOG.debug("Loaded index: %s (type: %s)", index_path, type(tree).__name__)

            # If index is not SBT (e.g., ZipFileLinearIndex), rebuild as SBT
            if not hasattr(tree, "add_node"):
                warning_msg = "Index is not SBT. Rebuilding as SBT for updates."
                LOG.warning(warning_msg)
                warnings.append(warning_msg)
                existing_sigs = list(tree.signatures())
                tree = sourmash.sbtmh.create_sbt_index()
                for s in existing_sigs:
                    leaf = sourmash.sbtmh.SigLeaf(s.md5sum(), s)
                    tree.add_node(leaf)

        except (ValueError, FileNotFoundError):
            LOG.info("Index not found or invalid. Creating new SBT index.")
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
            LOG.info("Updated index saved to %s", index_path)
        except PermissionError as err:
            LOG.error("Dont have permission to write file to disk")
            raise err

    added_sigs = [sig.name for sig in signatures]
    LOG.info("Added signatures to index: %s", ", ".join(added_sigs))
    return True, added_sigs, warnings


def remove_signatures_from_index(sample_ids: list[str], cnf: Settings) -> bool:
    """Add genome signature file to sourmash index"""

    genome_index = get_sbt_index(cnf=cnf, check=False)
    sbt_lock_path = f"/tmp/{genome_index.name}.lock"
    lock = fasteners.InterProcessLock(sbt_lock_path)
    LOG.debug("Using lock: %s", sbt_lock_path)

    # remove signature from existing index
    # acquire lock to remove signatures from database
    LOG.debug(
        "Attempt to acquire lock to remove %d signatures from index...", len(sample_ids)
    )
    with lock:
        # check if index already exist
        index_path = get_sbt_index(cnf)
        old_index = sourmash.load_file_as_index(str(index_path))

        # add signatures not among the sample ids a new index
        LOG.info("Removing %d genome signatures from index", len(sample_ids))
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