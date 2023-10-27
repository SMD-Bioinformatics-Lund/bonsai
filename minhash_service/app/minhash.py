"""Operations on minhash signatures."""
import logging
import gzip
import pathlib
import sourmash
from typing import List
from app import config
import fasteners
from pydantic import BaseModel

LOG = logging.getLogger(__name__)


def add_genome_signature_file(sample_id: str, signature) -> pathlib.Path:
    """

    and create or update existing index if required.
    """
    # get signature directory
    LOG.info(f'Adding signature file for {sample_id}')
    signature_db = pathlib.Path(config.GENOME_SIGNATURE_DIR)
    # make db if signature db is not present
    if not signature_db.exists():
        signature_db.mkdir(parents=True, exist_ok=True)

    # check that signature doesnt exist
    signature_file = signature_db.joinpath(f"{sample_id}.sig")
    if signature_file.is_file():
        raise FileExistsError("Signature file already exists")

    # check if compressed and decompress data
    LOG.info('Check if signature is compressed')
    if signature[:2] == b"\x1f\x8b":
        LOG.debug("Decompressing gziped file")
        signature = gzip.decompress(signature)

    # save signature to file
    LOG.info("Writing genome signatures to file")
    try:
        with open(signature_file, "w") as out:
            print(signature.decode("utf-8"), file=out)
    except PermissionError:
        msg = f"Dont have permission to write file to disk, {signature_file}"
        LOG.error(msg)
        raise PermissionError(msg)

    return signature_file


def remove_genome_signature_file(sample_id: str) -> bool:
    """Remove an existing signature file from disk."""

    # get signature directory
    signature_db = pathlib.Path(config.GENOME_SIGNATURE_DIR)

    # get genome index
    sbt_filename = signature_db.joinpath("genomes.sbt.zip")

    # check that signature doesnt exist
    signature_file = signature_db.joinpath(f"{sample_id}.sig")
    if signature_file.is_file():
        # load signature to memory
        signature = next(
            sourmash.signature.load_signatures(
                signature_file, ksize=config.SIGNATURE_KMER_SIZE
            )
        )
        # remove file
        signature_file.unlink()
    else:
        raise FileNotFoundError(f"Signature file: {signature_file} not found")

    # remove signature to existing index
    sbt_filename = signature_db.joinpath("genomes.sbt.zip")
    if sbt_filename.is_file():
        LOG.debug("Append to existing file")
        tree = sourmash.load_file_as_index(str(sbt_filename))

        # add generated signature to bloom tree
        LOG.info("Adding genome signatures to index")
        leaf = sourmash.sbtmh.SigLeaf(signature.md5sum(), signature)
        tree.remove_many(leaf)

        try:
            tree.save(str(sbt_filename.resolve()))
        except PermissionError as err:
            LOG.error("Dont have permission to write file to disk")
            raise err
        return True
    LOG.info(f"Signature file: {signature_file} was removed")
    return False


def add_genome_signatures_to_index(signature_files: List[pathlib.Path]) -> bool:
    """Add genome signature file to sourmash index"""

    # get signature directory
    signature_db = pathlib.Path(config.GENOME_SIGNATURE_DIR)

    # get genome index
    sbt_filename = signature_db.joinpath("genomes.sbt.zip")
    sbt_lock_path = f"{str(sbt_filename)}.lock"
    lock = fasteners.InterProcessLock(sbt_lock_path)
    LOG.debug("Using lock: {sbt_lock_path}")

    signatures = []
    for file_path in signature_files:
        signature = next(
            sourmash.load_file_as_signatures(
                str(file_path.resolve()), ksize=config.SIGNATURE_KMER_SIZE
            )
        )
        signatures.append(signature)

    # add signature to existing index
    sbt_filename = signature_db.joinpath("genomes.sbt.zip")
    # acquire lock to append signatures to database
    LOG.debug(f"Attempt to acquire lock to append {len(signatures)} to index...")
    with lock:
        # check if index already exist
        if sbt_filename.is_file():
            LOG.debug("Append to existing file")
            tree = sourmash.load_file_as_index(str(sbt_filename.resolve()))
        else:
            LOG.debug("Create new index file")
            tree = sourmash.sbtmh.create_sbt_index()

        # add generated signature to bloom tree
        LOG.info(f"Adding {len(signatures)} genome signatures to index")
        for signature in signatures:
            leaf = sourmash.sbtmh.SigLeaf(signature.md5sum(), signature)
            tree.add_node(leaf)
        # save updated bloom tree
        try:
            tree.save(str(sbt_filename))
        except PermissionError as err:
            LOG.error("Dont have permission to write file to disk")
            raise err

    return True


class SimilarSignature(BaseModel):
    """Container for similar signature result"""

    sample_id: str
    similarity: float 
    path: str


SimilarSignatures = List[SimilarSignature]

def get_signatures_similar_to_reference(signature_file: str, min_similarity: float) -> SimilarSignatures:
    """Get find samples that are similar to reference sample.

    min_similarity - minimum similarity score to be included
    """

    # load sourmash index
    LOG.debug(f'Getting samples similar to: {signature_file}')
    signature_dir = pathlib.Path(config.GENOME_SIGNATURE_DIR)
    index_path = signature_dir.joinpath(f"genomes.sbt.zip")
    # ensure that index exist
    if not index_path.is_file():
        raise FileNotFoundError(f"Sourmash index does not exist: {index_path}")
    LOG.debug(f'Load index file to memory')
    tree = sourmash.load_file_as_index(str(index_path))

    # load reference sequence
    signature_file = pathlib.Path(signature_file)
    if not signature_file.is_file():
        raise FileNotFoundError(f"Signature file not found, {signature_file.name}")
    LOG.debug(f'Loading signatures in path: {str(signature_file)}')
    query_signature = list(
        sourmash.load_file_as_signatures(str(signature_file), ksize=config.SIGNATURE_KMER_SIZE)
    )
    if len(query_signature) == 0:
        raise ValueError(f"No signature in: {signature_file.name} with kmer size: {config.SIGNATURE_KMER_SIZE}")
    else:
        query_signature = query_signature[0]

    # query for similar sequences
    LOG.debug(f'Searching for signatures with similarity > {min_similarity}')
    result = tree.search(query_signature, threshold=min_similarity)

    # read sample information of similar samples
    samples = []
    for itr_no, (similarity, found_sig, _) in enumerate(result):
        # read sample results
        signature_path = pathlib.Path(found_sig.filename)
        # extract sample id from sample name
        base_fname = signature_path.name[: -len(signature_path.suffix)]
        samples.append(SimilarSignature(
            sample_id=base_fname, similarity=similarity, path=str(signature_path.absolute())))
    return samples