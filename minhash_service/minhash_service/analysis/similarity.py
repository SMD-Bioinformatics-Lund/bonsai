"""Operations on minhash signatures."""

import logging

from sourmash.sbt import SBT
from sourmash.search import (
    SearchResult,
    search_databases_with_abund_query,
    search_databases_with_flat_query,
)
from sourmash.signature import SourmashSignature

from minhash_service.signatures.index import BaseIndexStore

from .models import AniEstimateOptions

LOG = logging.getLogger(__name__)


def get_similar_signatures(
    query_sig: SourmashSignature,
    index_repo: BaseIndexStore,
    min_similarity: float,
    ani_estimate: AniEstimateOptions = AniEstimateOptions.JACCARD,
    limit: int | None = None,
    ignore_abundance: bool = False,
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
                [index_repo.index],
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
            [index_repo.index],
            threshold=min_similarity,
            do_containment=containment,
            do_max_containment=max_containment,
            best_only=best_only,
            unload_data=True,
            estimate_ani_ci=False,
        )
    return results
