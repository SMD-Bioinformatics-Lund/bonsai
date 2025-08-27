"""Operations on minhash signatures."""

import logging
from pathlib import Path

import sourmash
from sourmash.index import IndexSearchResult as Result
from sourmash.sbt import SBT

from minhash_service.config import Settings
from minhash_service.minhash.models import SimilarSignature, SimilarSignatures

from .io import get_sbt_index, read_signature

LOG = logging.getLogger(__name__)


def get_similar_signatures(
    signature_file: Path, cnf: Settings, min_similarity: float, limit: int | None = None
) -> SimilarSignatures:
    """Get find samples that are similar to reference sample.

    min_similarity - minimum similarity score to be included
    """
    LOG.info(
        "Finding similar: %s; similarity: %f, limit: %d",
        signature_file.name,
        min_similarity,
        limit,
    )

    # load sourmash index
    LOG.debug("Getting samples similar to: %s", signature_file.name)
    index_path = get_sbt_index(cnf)
    LOG.debug("Load index file to memory")
    db: SBT = sourmash.load_file_as_index(str(index_path))

    # load reference sequence
    query_signature = read_signature(signature_file, cnf)[0]

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
    LOG.info("Found %d samples similar to %s", len(samples), signature_file.name)
    return samples
