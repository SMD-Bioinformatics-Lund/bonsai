"""Test functions for clustering."""

import pytest
from pathlib import Path

from minhash_service.analysis.cluster import ClusterMethod, cluster_signatures
from ..utils import get_data_path


@pytest.mark.parametrize(
    "sample_ids,cluster_method",
    [
        (["DRR237260.sig", "DRR237261.sig"], ClusterMethod.SINGLE),
        (["DRR237260.sig", "DRR237261.sig"], ClusterMethod.COMPLETE),
        (["DRR237260.sig", "DRR237261.sig"], ClusterMethod.AVERAGE),
        (["DRR237260.sig", "DRR237261.sig", "DRR237262.sig"], ClusterMethod.SINGLE),
        (["DRR237260.sig", "DRR237261.sig", "DRR237262.sig"], ClusterMethod.COMPLETE),
        (["DRR237260.sig", "DRR237261.sig", "DRR237262.sig"], ClusterMethod.AVERAGE),
    ],
)
def test_cluster_signatures(data_dir: Path, sample_ids: list[str], cluster_method: ClusterMethod):
    """Test function for clustering signatures."""
    sample_files: list[Path] = [get_data_path(data_dir, sid) for sid in sample_ids]

    nwk = cluster_signatures(signature_files=sample_files, kmer_size=31, method=cluster_method)

    # test that a longer string was returned
    assert nwk is not None and len(nwk) > 0


def test_cluster_single_signatures(data_dir: Path):
    """Test clustering only a single."""
    signature = get_data_path(data_dir, "DRR237260.sig")

    with pytest.raises(ValueError):
        cluster_signatures(signature_files=[signature], kmer_size=31, method=ClusterMethod.SINGLE)
