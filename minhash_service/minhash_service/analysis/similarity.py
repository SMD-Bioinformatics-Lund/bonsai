"""Operations on minhash signatures."""

import logging
import time
from csv import DictReader
from pathlib import Path
from tempfile import TemporaryDirectory

from sourmash_plugin_branchwater import sourmash_plugin_branchwater

from minhash_service.signatures.index import BaseIndexStore

from .models import AniEstimateOptions, SimilaritySearchConfig, SimilarSearchResult, SimilarResult

LOG = logging.getLogger(__name__)


SimilaritySearchResults = list[SimilarResult]


def parse_manysearch_results(path: Path) -> SimilaritySearchResults:
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


def filter_search_results(results: SimilaritySearchResults, min_similarity: float | None = None, limit: int | None = None) -> SimilaritySearchResults:
    """Filter similarity search results based on minimum similarity and limit."""
    if min_similarity is not None:
        results = [r for r in results if r.jaccard_similarity is not None and r.jaccard_similarity >= min_similarity]
    if limit is not None:
        results = results[:limit]
    return results


def get_similar_signatures(
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
            result = filter_search_results(result, min_similarity=config.min_similarity, limit=config.limit)
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
