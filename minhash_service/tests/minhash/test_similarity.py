"""Test functions in similarity file."""

import pytest

from minhash_service.config import Settings
from minhash_service.minhash.similarity import get_similar_signatures


@pytest.mark.parametrize("limit,exp_samples", [(None, 4), (4, 4), (2, 2)])
def test_get_similar_signatures(
    settings: Settings, limit: int | None, exp_samples: int
):
    sigs = get_similar_signatures(
        sample_id="DRR237260", min_similarity=0.5, limit=limit, cnf=settings
    )

    # test that sample id was set for all samples
    assert all([sig.sample_id != "" for sig in sigs])

    # test that limit was respected
    assert len(sigs) == exp_samples
