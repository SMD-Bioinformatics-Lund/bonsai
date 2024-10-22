"""Test cluster samples using ms_tree."""

import pytest
from allele_cluster_service.tasks import cluster


@pytest.mark.parametrize(
    "cluster_method,expected",
    [
        (
            "MSTree",
            "((DRR237260:0,DRR237261:0,DRR237262:0,DRR237263:0,DRR237264:0):0);",
        ),
        (
            "MSTreeV2",
            "((DRR237260:0,DRR237261:0,DRR237262:0,DRR237263:0,DRR237264:0):0);",
        ),
    ],
)
def test_cluster_task_same_mlst_profile(
    mlst_profiles_all_same, cluster_method, expected
):
    """Test task cluster using samples with the same MLST profile."""
    newick = cluster(profile=mlst_profiles_all_same, method=cluster_method)
    assert newick == expected


def test_cluster_task_w_nj_n_same_mlst_profile(mlst_profiles_all_same):
    """Test that ms_tree throws error if samples are to similar."""
    with pytest.raises(ValueError):
        # test NJ
        cluster(profile=mlst_profiles_all_same, method="NJ")

        # test rapid NJ
        cluster(profile=mlst_profiles_all_same, method="RapidNJ")


@pytest.mark.parametrize(
    "cluster_method,expected",
    [
        ("MSTree", "(DRR237264:2,DRR237262:1,DRR237260:1,DRR237263:1,DRR237261:0);"),
        ("MSTreeV2", "(DRR237264:2,DRR237262:1,DRR237260:1,DRR237263:1,DRR237261:0);"),
        (
            "NJ",
            "(DRR237264:1.00107,DRR237262:1.00357,(DRR237260:1.00357,(DRR237261:0.00499262,DRR237263:1.00357):1.25e-07):1.25e-07);",
        ),
        (
            "RapidNJ",
            "(DRR237264:1.00105,((DRR237261:0.0049927,DRR237262:1.0036):0,DRR237260:1.0036):0,DRR237263:1.0036);",
        ),
    ],
)
def test_cluster_task_different_mlst_profile(
    mlst_profiles_different, cluster_method, expected
):
    """Test task cluster using samples with different MLST profile."""
    newick = cluster(profile=mlst_profiles_different, method=cluster_method)
    assert newick == expected
