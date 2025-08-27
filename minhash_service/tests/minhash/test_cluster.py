"""Test functions for clustering."""

import pytest

from minhash_service.config import Settings
from minhash_service.minhash.cluster import ClusterMethod, cluster_signatures


@pytest.mark.parametrize(
    "sample_ids,cluster_method",
    [
        (["DRR237260", "DRR237261"], ClusterMethod.SINGLE),
        (["DRR237260", "DRR237261"], ClusterMethod.COMPLETE),
        (["DRR237260", "DRR237261"], ClusterMethod.AVERAGE),
        (["DRR237260", "DRR237261", "DRR237262"], ClusterMethod.SINGLE),
        (["DRR237260", "DRR237261", "DRR237262"], ClusterMethod.COMPLETE),
        (["DRR237260", "DRR237261", "DRR237262"], ClusterMethod.AVERAGE),
    ],
)
def test_cluster_signatures(
    settings: Settings, sample_ids: list[str], cluster_method: ClusterMethod
):
    """Test function for clustering signatures."""

    nwk = cluster_signatures(sample_ids=sample_ids, method=cluster_method, cnf=settings)

    # test that a longer string was returned
    assert nwk is not None and len(nwk) > 0


def test_cluster_single_signatures(settings: Settings):
    """Test clustering only a single."""

    with pytest.raises(ValueError):
        cluster_signatures(
            sample_ids=["DRR237260"], method=ClusterMethod.SINGLE, cnf=settings
        )
