"""Test functions in similarity file."""

import pytest
from pathlib import Path

from minhash_service.analysis.similarity import get_similar_signatures
from minhash_service.analysis.models import SimilaritySearchConfig
from minhash_service.signatures.index import SBTIndexStore
from minhash_service.signatures.io import read_signatures

from ..utils import get_data_path


@pytest.mark.parametrize("limit,exp_samples", [(None, 4), (4, 4), (2, 2)])
def test_get_similar_signatures(data_dir: Path, limit: int | None, exp_samples: int):
    cnf = SimilaritySearchConfig(min_similarity=0.5, limit=limit)
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
