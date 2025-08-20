"""Functions for reading and writing signatures"""

import gzip
import logging
import os
import tempfile
from pathlib import Path
from typing import Callable, Iterable

import sourmash
from sourmash.signature import FrozenSourmashSignature, SourmashSignature

from minhash_service.config import Settings

from .paths import get_signature_path

LOG = logging.getLogger(__name__)
Signatures = list[SourmashSignature | FrozenSourmashSignature]


def read_signature(sample_id: str, kmer_size: int) -> Signatures:
    """Read signature to memory."""
    # read signature
    signature_path = get_signature_path(sample_id)
    loaded = sourmash.load_file_as_signatures(signature_path, ksize=kmer_size)

    # check that were signatures loaded with current kmer
    loaded_sigs = list(loaded)
    if len(loaded_sigs) == 0:
        raise ValueError(
            f"No signatures, sample id: {sample_id}, ksize: {kmer_size}, {loaded}"
        )
    return loaded_sigs


def _signature_writer(path: Path, signatures, compress: bool):
    """Small writer utility."""
    if compress:
        # Wrap gzip over a text writer
        with gzip.open(path, "wt", encoding="utf-8") as out:
            sourmash.signature.save_signatures_to_json(signatures, out)
    else:
        with open(path, "w", encoding="utf-8") as out:
            sourmash.signature.save_signatures_to_json(signatures, out)


def save_signature_file(
    sample_id: str,
    payload: bytes | bytearray | memoryview,
    cnf: Settings,
    compress: bool = False,
):
    """Save a sourmash signature to disk.

    - Accepts raw JSON bytes; if gzipped (by magic bytes), transparently decompresses.
    - Loads one or more signatures from JSON, sets `name = sample_id` and `filename`
      to the target file's basename, and writes them back to disk (optionally gzipped).
    - Returns the final file path.

    Notes:
      * This function does NOT update/append to any sourmash index; it only writes
        the signature file on disk.

    """
    # resolve directories
    signature_dir = Path(cnf.signature_dir)
    signature_dir.mkdir(parents=True, exist_ok=True)

    signature_path = get_signature_path(sample_id, ensure_exists=False)
    if compress and not str(signature_path).endswith(".gz"):
        signature_path = signature_path.with_suffix(signature_path.suffix + ".gz")

    LOG.info("Saving signature file for %s to %s", sample_id, signature_path)

    # Ensure bytes-like
    if isinstance(payload, memoryview):
        payload = payload.tobytes()

    # check if compressed and decompress data
    try:
        if payload[:2] == b"\x1f\x8b":
            LOG.debug("Input seem to be gzipped; decompressing")
            payload = gzip.decompress(payload)
    except (OSError, gzip.BadGzipFile) as err:
        LOG.exception(
            "Failed to decompress gzipped payload for sample_id=%s", sample_id
        )
        raise ValueError("Invalid gzipped signature payload") from err

    # convert JSON bytes -> sourmash signature
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as e:
        LOG.exception("Signature JSON is not valid UTF-8 for sample_id=%s", sample_id)
        raise ValueError("Signature JSON must be UTF-8 encoded") from e

    try:
        sig_iter: Iterable[FrozenSourmashSignature] = (
            sourmash.signature.load_signatures_from_json(text, ksize=cnf.kmer_size)
        )
    except Exception as e:
        LOG.exception("Failed to parse signature JSON for sample_id=%s", sample_id)
        raise ValueError("Invalid signature JSON") from e

    # Normalize signatures: set name and filename
    upd_signatures: list[FrozenSourmashSignature] = []
    outfile_name = signature_path.name
    for sig_obj in sig_iter:
        upd_sig = sig_obj.to_mutable()
        upd_sig.name = sample_id
        upd_sig.filename = outfile_name
        upd_signatures.append(upd_sig.to_frozen())

    if not upd_signatures:
        raise ValueError("No signatures found in payload")

    # atomic write signature to disk
    atomic_save(
        signature_path,
        write_to_path=lambda tmp_path: _signature_writer(
            tmp_path, upd_signatures, compress
        ),
    )
    return signature_path


def remove_signature_file(sample_id: str) -> bool:
    """Remove an existing signature file from filesystem."""
    try:
        signature_file = get_signature_path(sample_id, ensure_exists=True)
        signature_file.unlink()
    except Exception:
        return False
    LOG.info("Signature file: %s was removed", signature_file)
    return True


def atomic_save(
    path: str | Path,
    *,
    write_to_path: Callable[[Path], None],
    tmp_suffix: str = ".tmp",
    make_dirs: bool = True,
    sync: bool = True,
    perms: int | None = None,
    inherit_perms_from: str | Path | None = None,
) -> Path:
    """
    Atomically write to `path` by writing to a temporary file in the same
    directory and then replacing.

    Parameters
    ----------
    path : str | Path
        Final destination path.
    write_to_path : Callable[[Path], None]
        A function that receives the temporary path and is responsible for
        writing all file contents to it (open/close inside).
    tmp_suffix : str
        Suffix appended to the temp file.
    make_dirs : bool
        Create parent directories if missing.
    sync : bool
        If True, fsync the file and parent directory (where supported).
    perms : Optional[int]
        If provided, chmod the temp file to these permissions before replace.
    inherit_perms_from : str | Path | None
        If provided and exists, copy its mode (st_mode) to the temp file
        before replace.

    Returns
    -------
    Path
        The final path.

    Raises
    ------
    Any exception raised by `write_to_path` or OS operations will bubble up.
    """
    dest = Path(path)
    parent = dest.parent

    if make_dirs:
        parent.mkdir(parents=True, exist_ok=True)

    # Create a temp file in the same directory to guarantee same filesystem
    with tempfile.NamedTemporaryFile(
        dir=parent, prefix=dest.name, suffix=tmp_suffix, delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Let the caller write to the temp path (open/close is their job)
        write_to_path(tmp_path)

        # Optionally set/inherit permissions
        if inherit_perms_from:
            src = Path(inherit_perms_from)
            if src.exists():
                st = src.stat()
                tmp_path.chmod(st.st_mode)
        elif perms is not None:
            tmp_path.chmod(perms)

        # Best-effort fsync of the file contents
        if sync:
            try:
                fd = os.open(tmp_path, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            except Exception:
                # Not fatal; proceed to replace
                pass

        # Atomic replace
        tmp_path.replace(dest)

        # Fsync the directory entry where possible (POSIX)
        if sync:
            try:
                dir_fd = os.open(parent, os.O_DIRECTORY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except Exception:
                # On Windows or certain FS, O_DIRECTORY may not exist; ignore
                pass

        return dest
    except Exception:
        # Cleanup on failure
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        raise
