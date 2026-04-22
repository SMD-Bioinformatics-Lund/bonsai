"""Operations on minhash signatures."""

import logging
from typing import cast

from sourmash.search import (SearchResult, search_databases_with_abund_query,
                             search_databases_with_flat_query)
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
        "Finding similar samples - query: %s; similarity: %f, limit: %s",
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
    if config.limit is not None:
        n_hits_to_include = min([len(results), config.limit])
        results = results[:n_hits_to_include]
    return results


def parse_manysearch_results(path: Path) -> list[SimilarResult]:
    """Parse sourmash branchwater multisearch results."""
    result = []
    reader = DictReader(path.open(encoding="utf-8"), delimiter=",")
    for row in reader:
        result.append(
            SimilarResult(
                name=row["match_name"],
                md5=row["match_md5"],
                containment=float(row["containment"]),
                jaccard_similarity=None if row["jaccard"] == "" else float(row["jaccard"]),
                max_containment=None if row["max_containment"] == "" else float(row["max_containment"]),
            )
        )
    return result


def get_similar_signatures_v2(
    query_sig: Path,
    index_repo: BaseIndexStore,
    config: SimilaritySearchConfig,
) -> SimilarSearchResult:
    """WIP verion which uses branchwater multisearch to find similar signatures."""
    LOG.info(
        "Finding similar samples - query: %s; similarity: %f, limit: %s",
        query_sig.name,
        config.min_similarity,
        config.limit,
    )
    # define query params
    output_all = config.min_similarity is None and config.limit is None

    # do multisearch
    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.csv"
        start_execution = time.time()
        exit_status = sourmash_plugin_branchwater.do_multisearch(
            str(query_sig.absolute()),
            str(index_repo.index_path.absolute()),
            threshold=config.min_similarity,
            ksize=config.ksize,
            scaled=config.scaled,
            moltype=config.moltype,
            estimate_ani=config.estimate_ani,
            estimate_prob_overlap=config.estimate_prob_overlap,
            output_all_comparisons=output_all,
            calc_abund_stats=config.calc_abund_stats,
            output_path=str(output_path.absolute()),
        )
        if exit_status != 0:
            raise ValueError(f"Branchwater multisearch failed with status {exit_status}")
        
        try:
            result = parse_manysearch_results(output_path)
        except Exception as exc:
            LOG.error("Error parsing branchwater multisearch results: %s", exc)
            raise
        execution_time = time.time() - start_execution

    return SimilarSearchResult(
        query=query_sig.name,
        ksize=config.ksize,
        moltype=config.moltype,
        search_time=execution_time,
        matches=result,
    )
