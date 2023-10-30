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