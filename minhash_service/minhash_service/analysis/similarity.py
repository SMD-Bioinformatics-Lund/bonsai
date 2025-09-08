"""Operations on minhash signatures."""

import logging
from typing import cast

from sourmash.search import (
    SearchResult,
    search_databases_with_abund_query,
    search_databases_with_flat_query,
)
from sourmash.signature import SourmashSignature

from minhash_service.signatures.index import BaseIndexStore

from .models import AniEstimateOptions, SimilaritySearchConfig

LOG = logging.getLogger(__name__)


SimilaritySearchResults = list[SearchResult]


def get_similar_signatures(
    query_sig: SourmashSignature,
    index_repo: BaseIndexStore,
    config: SimilaritySearchConfig,
) -> SimilaritySearchResults:
    """Get find samples that are similar to reference sample.

    min_similarity - minimum similarity score to be included
    """
    LOG.info(
        "Finding similar: %s; similarity: %f, limit: %d",
        query_sig.name,
        config.min_similarity,
        config.limit,
    )
    # define query params
    best_only = config.limit == 1
    max_containment = False

    match config.ani_estimate:
        case AniEstimateOptions.CONTAINMENT:
            containment = True
            max_containment = False
        case AniEstimateOptions.MAX_CONTAINMENT:
            containment = False
            max_containment = True
        case _:
            containment = False
            max_containment = False

    if query_sig.minhash.track_abundance and config.ignore_abundance:
        query_sig.minhash = query_sig.minhash.flatten()

    # do the acctual query
    results: SimilaritySearchResults = []
    if query_sig.minhash.track_abundance:
        try:
            results = cast(
                SimilaritySearchResults,
                search_databases_with_abund_query(
                    query=query_sig,
                    databases=[index_repo.index],
                    threshold=config.min_similarity,
                    do_containment=containment,
                    do_max_containment=max_containment,
                    best_only=best_only,
                    unload_data=True,
                ),
            )
        except TypeError as exc:
            LOG.error("Sourmash error: %s", exc)
            raise
    else:
        results = cast(
            SimilaritySearchResults,
            search_databases_with_flat_query(
                query=query_sig,
                databases=[index_repo.index],
                threshold=config.min_similarity,
                do_containment=containment,
                do_max_containment=max_containment,
                best_only=best_only,
                unload_data=True,
                estimate_ani_ci=False,
            ),
        )
    return results
