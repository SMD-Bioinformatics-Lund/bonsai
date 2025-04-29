"""Operations on minhash signatures."""

import logging

import sourmash
from pydantic import BaseModel
from sourmash.index import IndexSearchResult as Result
from sourmash.sbt import SBT

from minhash_service.config import Settings

from .io import get_sbt_index, read_signature

LOG = logging.getLogger(__name__)


class SimilarSignature(BaseModel):  # pydantic: disable=too-few-public-methods
    """Container for similar signature result"""

    sample_id: str
    similarity: float


SimilarSignatures = list[SimilarSignature]


def get_similar_signatures(
    sample_id: str, cnf: Settings, min_similarity: float, limit: int | None = None
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
    index_path = get_sbt_index(cnf)
    LOG.debug("Load index file to memory")
    db: SBT = sourmash.load_file_as_index(str(index_path))

    # load reference sequence
    query_signature = read_signature(sample_id, cnf)[0]

    # query for similar sequences
    LOG.debug("Searching for signatures with similarity > %f", min_similarity)
    result: list[Result] = db.search(
        query_signature, threshold=min_similarity
    )  # read sample information of similar samples

    samples: list[SimilarSignature] = []
    for itr_no, (similarity, sig, _) in enumerate(result, start=1):
        # extract sample id from sample name
        sid = sig.filename.split("_")[0] if sig.name == "" else sig.name
        signature_path = index_path.joinpath(sig.filename)
        LOG.info("no %d - path: %s -> %s", itr_no, signature_path, sid)
        samples.append(SimilarSignature(sample_id=sid, similarity=similarity))

        # break iteration if limit is reached
        if isinstance(limit, int) and limit == itr_no:
            break
    LOG.info("Found %d samples similar to %s", len(samples), sample_id)
    return samples
