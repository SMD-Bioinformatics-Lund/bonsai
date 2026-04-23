"""Test functions in similarity file."""

from pathlib import Path

import pytest

from minhash_service.analysis.models import SimilaritySearchConfig, SimilarResult
from minhash_service.analysis.similarity import filter_search_results, get_similar_signatures, parse_manysearch_results
from minhash_service.signatures.index import RocksDBIndexStore

from ..utils import get_data_path


@pytest.mark.parametrize("limit,exp_samples", [(None, 4), (4, 4), (2, 2)])
def test_get_similar_signatures_no_dupl(data_dir: Path, limit: int | None, exp_samples: int):
    """Test get similar signatures with no duplicates in the index."""

    cnf = SimilaritySearchConfig(min_similarity=0.5, ksize=31, limit=limit)

    # read query signature
    query_path = get_data_path(data_dir, "DRR237260.sig")

    # get index
    idx_path = get_data_path(data_dir, "rocksdb31.all")
    idx = RocksDBIndexStore(idx_path)

    # query
    result = get_similar_signatures(query_path, idx, config=cnf)

    # test that limit was respected
    assert len(result.matches) == exp_samples


def test_get_similar_signatures_dupl(data_dir: Path):
    """Test get duplicated signatures in the index."""

    cnf = SimilaritySearchConfig(min_similarity=0.5, ksize=31)

    # read query signature
    query_path = get_data_path(data_dir, "DRR237260.sig")

    # get index
    idx_path = get_data_path(data_dir, "rocksdb31.duplicates")
    idx = RocksDBIndexStore(idx_path)

    result = get_similar_signatures(query_path, idx, config=cnf)

    # assert that both the query and duplicate was found
    matches = [m.name for m in result.matches]
    assert set(["DRR237260", "DRR237260.dupl"]).issubset(set(matches))


def test_parse_multisearch_results(data_dir: Path):
    """Test parsing of branchwater multisearch results."""

    result_file = get_data_path(data_dir, "multisearch_results.out")

    results = parse_manysearch_results(result_file)

    # Assert correct output format
    assert isinstance(results, list)
    assert isinstance(results[0], SimilarResult)

    # Assert that all hits was parsed
    assert len(results) == 3
    assert results[0].name == "DRR237261"


def test_filter_search_results(data_dir: Path):
    """Test filtering of similarity search results."""

    result_file = get_data_path(data_dir, "multisearch_results.out")
    results = parse_manysearch_results(result_file)

    # filter with min_similarity
    filtered = filter_search_results(results, min_similarity=0.999)
    assert len(filtered) == 2
    assert all(r.jaccard_similarity >= 0.999 for r in filtered)

    # filter with limit
    filtered = filter_search_results(results, limit=2)
    assert len(filtered) == 2

    checksums = [
        "c3325498b73ef2668ad4afa2802948f5",
        "bb95e9ec1ed6d5b4c5a8694fd6e020c6", 
    ]
    filtered = filter_search_results(results, subset_checksums=checksums)
    assert len(filtered) == 2

    filtered = filter_search_results(results, subset_checksums=checksums, limit=1)
    assert len(filtered) == 1