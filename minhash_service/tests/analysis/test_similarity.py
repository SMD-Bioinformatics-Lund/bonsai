"""Test functions in similarity file."""

from pathlib import Path

import pytest

from minhash_service.analysis.models import SimilaritySearchConfig, SimilarResult
from minhash_service.analysis.similarity import get_similar_signatures, get_similar_signatures_v2, parse_manysearch_results
from minhash_service.signatures.index import SBTIndexStore, RocksDBIndexStore
from minhash_service.signatures.io import read_signatures

from ..utils import get_data_path


@pytest.mark.parametrize("limit,exp_samples", [(None, 4), (4, 4), (2, 2)])
def test_get_similar_signatures_no_dupl(data_dir: Path, limit: int | None, exp_samples: int):
    """Test get similar signatures with no duplicates in the index."""

    cnf = SimilaritySearchConfig(min_similarity=0.5, ksize=31, limit=limit)
    # read query signature
    query_path = get_data_path(data_dir, "DRR237260.sig")
    query_sig = read_signatures(query_path, 31)

    # get index
    idx_path = get_data_path(data_dir, "index.all.sbt.zip")
    idx = SBTIndexStore(idx_path)

    # query
    sigs = get_similar_signatures(query_sig[0], idx, config=cnf)

    # test that limit was respected
    assert len(sigs) == exp_samples


def test_get_similar_signatures_dupl(data_dir: Path):
    """Test get duplicated signatures in the index."""

    cnf = SimilaritySearchConfig(min_similarity=0.5, ksize=31)

    # read query signature
    query_path = get_data_path(data_dir, "DRR237260.sig")

    # get index
    idx_path = get_data_path(data_dir, "rocksdb31.duplicates")
    idx = RocksDBIndexStore(idx_path)

    result = get_similar_signatures_v2(query_path, idx, config=cnf)

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