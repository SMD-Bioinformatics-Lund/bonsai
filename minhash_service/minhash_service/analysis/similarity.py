"""Operations on minhash signatures."""

import logging

from sourmash.sbt import SBT
from sourmash.search import search_databases_with_abund_query, search_databases_with_flat_query, SearchResult
from sourmash.signature import SourmashSignature

from minhash_service.signatures.index import BaseIndexStore
from .models import AniEstimateOptions

LOG = logging.getLogger(__name__)


def get_similar_signatures_v2(
    query_sig: SourmashSignature, index: BaseIndexStore, 
    min_similarity: float, ani_estimate: AniEstimateOptions = AniEstimateOptions.JACCARD, 
    limit: int | None = None, ignore_abundance: bool = False
) -> SearchResult:
    """Get find samples that are similar to reference sample.

    min_similarity - minimum similarity score to be included
    """
    LOG.info(
        "Finding similar: %s; similarity: %f, limit: %d",
        query_sig.name,
        min_similarity,
        limit,
    )
    # define query params
    best_only = limit == 1
    containment = False
    max_containment = False

    match ani_estimate:
        case AniEstimateOptions.CONTAINMENT:
            containment = True
        case AniEstimateOptions.MAX_CONTAINMENT:
            max_containment = True
    
    if query_sig.minhash.track_abundance and ignore_abundance:
        query_sig.minhash = query_sig.minhash.flatten()

    # do the acctual query
    results: list[SearchResult] = []
    if query_sig.minhash.track_abundance:
        try:
            results = search_databases_with_abund_query(
                query_sig,
                [index],
                threshold=min_similarity,
                do_containment=containment,
                do_max_containment=max_containment,
                best_only=best_only,
                unload_data=True,
            )
        except TypeError as exc:
            LOG.error("Sourmash error: %s", exc)
            raise
    else:
        results = search_databases_with_flat_query(
            query_sig,
            [index],
            threshold=min_similarity,
            do_containment=containment,
            do_max_containment=max_containment,
            best_only=best_only,
            unload_data=True,
            estimate_ani_ci=False,
        )
    return results

# def get_similar_signatures(
#     signature_file: Path, cnf: Settings, min_similarity: float, limit: int | None = None
# ) -> SimilarSignatures:
#     """Get find samples that are similar to reference sample.

#     min_similarity - minimum similarity score to be included
#     """
#     LOG.info(
#         "Finding similar: %s; similarity: %f, limit: %d",
#         signature_file.name,
#         min_similarity,
#         limit,
#     )

#     # load sourmash index
#     LOG.debug("Getting samples similar to: %s", signature_file.name)
#     index_path = get_sbt_index(cnf)
#     LOG.debug("Load index file to memory")
#     db: SBT = sourmash.load_file_as_index(str(index_path))

#     # load reference sequence
#     query_signature = read_signature(signature_file, cnf)[0]

#     # query for similar sequences
#     LOG.debug("Searching for signatures with similarity > %f", min_similarity)
#     result: list[Result] = db.search(
#         query_signature, threshold=min_similarity
#     )  # read sample information of similar samples

#     samples: list[SimilarSignature] = []
#     for itr_no, (similarity, sig, _) in enumerate(result, start=1):
#         # extract sample id from sample name
#         sid = sig.filename.split("_")[0] if sig.name == "" else sig.name
#         signature_path = index_path.joinpath(sig.filename)
#         LOG.info("no %d - path: %s -> %s", itr_no, signature_path, sid)
#         samples.append(SimilarSignature(sample_id=sid, similarity=similarity))

#         # break iteration if limit is reached
#         if isinstance(limit, int) and limit == itr_no:
#             break
#     LOG.info("Found %d samples similar to %s", len(samples), signature_file.name)
#     return samples
