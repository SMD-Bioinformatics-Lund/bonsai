"""Operations on minhash signatures."""
import logging
import pathlib
from typing import List

import sourmash
from minhash_service.config import settings
from pydantic import BaseModel

from .io import SIGNATURES, get_sbt_index, read_signature

LOG = logging.getLogger(__name__)


class SimilarSignature(BaseModel):  # pydantic: disable=too-few-public-methods
    """Container for similar signature result"""

    sample_id: str
    similarity: float


SimilarSignatures = List[SimilarSignature]


def get_similar_signatures(
    sample_id: str, min_similarity: float, limit: int | None = None
) -> SimilarSignatures:
    """Get find samples that are similar to reference sample.

    min_similarity - minimum similarity score to be included
    """
    LOG.info(
        "Finding similar: %s; similarity: %f, limit: %d",
        sample_id,
        min_similarity,
        limit,
    )

    # load sourmash index
    LOG.debug("Getting samples similar to: %s", sample_id)
    index_path: pathlib.Path = get_sbt_index()
    LOG.debug("Load index file to memory")
    db = sourmash.load_file_as_index(index_path)

    # load reference sequence
    query_signature: SIGNATURES = read_signature(sample_id)
    query_signature = query_signature[0]
    if len(query_signature) == 0:
        msg = (
            f"No signature in: {query_signature.filename}"
            f"with kmer size: {settings.kmer_size}"
        )
        raise ValueError(msg)

    # query for similar sequences
    LOG.debug("Searching for signatures with similarity > %f", min_similarity)
    result = db.search(
        query_signature, threshold=min_similarity
    )  # read sample information of similar samples
    samples = []

    for itr_no, (similarity, found_sig, _) in enumerate(result, start=1):
        # read sample results
        signature_path = pathlib.Path(f"{found_sig.name}.sig")
        # extract sample id from sample name
        base_fname = found_sig.name
        LOG.info("no %d - path: %s -> %s", itr_no, signature_path, base_fname)
        samples.append(SimilarSignature(sample_id=base_fname, similarity=similarity))

        # break iteration if limit is reached
        if isinstance(limit, int) and limit == itr_no:
            break
    LOG.info("Found %d samples similar to %s", len(samples), sample_id)
    return samples
