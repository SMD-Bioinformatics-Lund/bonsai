"""Operations on minhash signatures."""
import logging
import pathlib
from typing import List

import sourmash
from pydantic import BaseModel

from minhash_service import config

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
            f"with kmer size: {config.SIGNATURE_KMER_SIZE}"
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
        signature_path = pathlib.Path(found_sig.filename)
        # extract sample id from sample name
        base_fname = signature_path.name[: -len(signature_path.suffix)]
        samples.append(SimilarSignature(sample_id=base_fname, similarity=similarity))

        # break iteration if limit is reached
        if isinstance(limit, int) and limit == itr_no:
            break
    LOG.info("Found %d samples similar to %s", len(samples), sample_id)
    return samples
