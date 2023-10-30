"""Operations on minhash signatures."""
import logging
import pathlib
import sourmash
from typing import List
from app import config
import fasteners
from pydantic import BaseModel
from .io import get_sbt_index


LOG = logging.getLogger(__name__)


class SimilarSignature(BaseModel):
    """Container for similar signature result"""

    sample_id: str
    similarity: float 


SimilarSignatures = List[SimilarSignature]


def add_signatures_to_index(sample_ids: List[str]) -> bool:
    """Add genome signature file to sourmash index"""

    genome_index = get_sbt_index(check=False)
    sbt_lock_path = f"{genome_index}.lock"
    lock = fasteners.InterProcessLock(sbt_lock_path)
    LOG.debug("Using lock: {sbt_lock_path}")

    signatures = []
    for sample_id in sample_ids:
        signature = _load_signature(sample_id)
        signatures.append(signature[0])

    # add signature to existing index
    # acquire lock to append signatures to database
    LOG.debug(f"Attempt to acquire lock to append {len(signatures)} to index...")
    with lock:
        # check if index already exist
        try:
            index_path = get_sbt_index()
            tree = sourmash.load_file_as_index(index_path)
        except FileNotFoundError:
            tree = sourmash.sbtmh.create_sbt_index()

        # add generated signature to bloom tree
        LOG.info(f"Adding {len(signatures)} genome signatures to index")
        for signature in signatures:
            leaf = sourmash.sbtmh.SigLeaf(signature.md5sum(), signature)
            tree.add_node(leaf)
        # save updated bloom tree
        try:
            index_path = get_sbt_index(check=False)
            tree.save(index_path)
        except PermissionError as err:
            LOG.error("Dont have permission to write file to disk")
            raise err

    return True


def get_similar_signatures(sample_id: str, min_similarity: float, limit: int | None = None) -> SimilarSignatures:
    """Get find samples that are similar to reference sample.

    min_similarity - minimum similarity score to be included
    """

    # load sourmash index
    LOG.debug(f'Getting samples similar to: {sample_id}')
    index_path: pathlib.Path = get_sbt_index()
    LOG.debug(f'Load index file to memory')
    db = sourmash.load_file_as_index(index_path)

    # load reference sequence
    query_signature = _load_signature(sample_id)
    if len(query_signature) == 0:
        raise ValueError(f"No signature in: {signature_file.name} with kmer size: {config.SIGNATURE_KMER_SIZE}")
    else:
        query_signature = query_signature[0]

    # query for similar sequences
    LOG.debug(f'Searching for signatures with similarity > {min_similarity}')
    result = db.search(query_signature, threshold=min_similarity) # read sample information of similar samples 
    samples = []

    for itr_no, (similarity, found_sig, _) in enumerate(result, start=1):
        # read sample results
        signature_path = pathlib.Path(found_sig.filename)
        # extract sample id from sample name
        base_fname = signature_path.name[: -len(signature_path.suffix)]
        samples.append(SimilarSignature(sample_id=base_fname, similarity=similarity))

        # break iteration if limit is reached
        if isinstance(limit, int) and limit == itr_no:
            break
    return samples