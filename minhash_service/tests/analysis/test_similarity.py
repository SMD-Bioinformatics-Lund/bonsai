"""Test functions in similarity file."""

from pathlib import Path

import pytest

# Installed from conda-forge in the service image; PyPI ships only a source
# tarball needing a Rust toolchain, so pip-based CI cannot provide it.
pytest.importorskip("sourmash_plugin_branchwater")

from minhash_service.analysis.models import SimilaritySearchConfig, SimilarResult
from minhash_service.analysis.similarity import (
    filter_search_results,
    get_similar_signatures,
    parse_manysearch_results,
)
from minhash_service.signatures.index import RocksDBIndexStore
from minhash_service.signatures.io import read_signatures

from ..utils import get_data_path


@pytest.mark.parametrize("limit,exp_samples", [(None, 4), (4, 4), (2, 2)])
def test_get_similar_signatures_no_dupl(
    data_dir: Path, tmp_path: Path, limit: int | None, exp_samples: int
):
    """Test get similar signatures with no duplicates in the index."""

    cnf = SimilaritySearchConfig(min_similarity=0.5, ksize=31, limit=limit)

    # read query signature
    query_path = get_data_path(data_dir, "DRR237260.sig")

    # get index
    idx = RocksDBIndexStore(tmp_path / "rocksdb")
    idx.replace_signatures(
        [
            sig
            for path in sorted(data_dir.glob("*.sig"))
            if ".dupl." not in path.name
            for sig in read_signatures(path, kmer_size=31)
        ]
    )

    # query
    result = get_similar_signatures(query_path, idx, config=cnf)

    # test that limit was respected
    assert len(result.matches) == exp_samples


def test_get_similar_signatures_dupl(data_dir: Path, tmp_path: Path):
    """Test get duplicated signatures in the index."""

    cnf = SimilaritySearchConfig(min_similarity=0.5, ksize=31)

    # read query signature
    query_path = get_data_path(data_dir, "DRR237260.sig")

    # get index
    from sourmash.index.revindex import DiskRevIndex

    idx = RocksDBIndexStore(tmp_path / "rocksdb")
    sigs = [
        sig
        for path in sorted(data_dir.glob("*.sig"))
        for sig in read_signatures(path, kmer_size=31)
    ]
    DiskRevIndex.create_from_sigs(sigs, str(idx.index_path))

    result = get_similar_signatures(query_path, idx, config=cnf)

    # Shared sample signatures are represented once at the checksum level.
    assert len({m.md5 for m in result.matches}) == len(result.matches)


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


def test_filter_search_results_deduplicates_before_limit(data_dir: Path):
    """Repeated index entries do not consume the checksum result limit."""
    result_file = get_data_path(data_dir, "multisearch_results.out")
    results = parse_manysearch_results(result_file)
    duplicated = [results[0], results[0].model_copy(), results[1]]

    filtered = filter_search_results(duplicated, limit=2)

    assert {result.md5 for result in filtered} == {results[0].md5, results[1].md5}


def test_limit_uses_similarity_order_and_stable_ties():
    def match(checksum, similarity):
        return SimilarResult(
            name=checksum,
            md5=checksum,
            containment=similarity,
            jaccard_similarity=similarity,
            max_containment=similarity,
        )

    results = [match("low", 0.6), match("b", 0.95), match("a", 0.95), match("a", 0.95)]
    assert [r.md5 for r in filter_search_results(results, limit=2)] == ["a", "b"]
