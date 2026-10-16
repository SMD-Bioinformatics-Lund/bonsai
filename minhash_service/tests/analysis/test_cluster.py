"""Test functions for clustering."""

import re
from pathlib import Path

import pytest
from scipy.cluster.hierarchy import ClusterNode
from sourmash import MinHash, SourmashSignature

from minhash_service.analysis.cluster import (
    ClusterMethod,
    cluster_signatures,
    tree_to_newick,
)
from minhash_service.signatures.io import read_signatures

from ..utils import get_data_path


@pytest.mark.parametrize("distance", [0.0, 0.004, 0.123456, 1.75, 12.875, 1e-10])
def test_newick_preserves_leaf_and_internal_branch_lengths(distance: float):
    """Small nonzero branches and fractional distances must survive export."""
    subtree = ClusterNode(3, ClusterNode(0), ClusterNode(1), distance)
    tree = ClusterNode(4, subtree, ClusterNode(2), 2 * distance)

    newick = tree_to_newick(tree, "", tree.dist, ["A", "B", "C"])

    leaves = {
        name: float(length)
        for name, length in re.findall(r"([ABC]):([^,();]+)", newick)
    }
    internal_lengths = [
        float(length) for length in re.findall(r"\):([^,();]+)", newick)
    ]
    assert leaves == {"A": distance, "B": distance, "C": 2 * distance}
    assert internal_lengths == [distance]


@pytest.mark.parametrize(
    "method,root_distance",
    [
        (ClusterMethod.SINGLE, 7 / 8),
        (ClusterMethod.COMPLETE, 1),
        (ClusterMethod.AVERAGE, 15 / 16),
    ],
)
def test_cluster_uses_jaccard_distances(method: ClusterMethod, root_distance: float):
    """Merge heights must use pairwise Jaccard distances, not similarity rows."""
    signatures = []
    for hashes in ([1, 2, 3, 4], [1, 2, 3, 4, 5], [5, 6, 7, 8]):
        minhash = MinHash(n=0, ksize=31, scaled=1)
        minhash.add_many(hashes)
        signatures.append(SourmashSignature(minhash))

    tree, checksums = cluster_signatures(signatures, method)

    # A and B share 4 of 5 hashes; B and C share 1 of 8; A and C share none.
    first_merge = next(node for node in (tree.left, tree.right) if not node.is_leaf())
    assert set(first_merge.pre_order()) == {0, 1}
    assert first_merge.dist == pytest.approx(1 / 5)
    assert tree.dist == pytest.approx(root_distance)
    assert checksums == [signature.md5sum() for signature in signatures]


@pytest.mark.parametrize("hashes,distance", [([1, 2], 0), ([3, 4], 1)])
def test_cluster_identical_and_disjoint_signatures(hashes: list[int], distance: float):
    """Identical and disjoint signatures have distances zero and one."""
    signatures = []
    for values in ([1, 2], hashes):
        minhash = MinHash(n=0, ksize=31, scaled=1)
        minhash.add_many(values)
        signatures.append(SourmashSignature(minhash))

    tree, _ = cluster_signatures(signatures, ClusterMethod.SINGLE)

    assert tree.dist == pytest.approx(distance)


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
def test_cluster_signatures(
    data_dir: Path, sample_ids: list[str], cluster_method: ClusterMethod
):
    """Test function for clustering signatures."""
    sample_files: list[Path] = [get_data_path(data_dir, sid) for sid in sample_ids]

    signature_obj = [read_signatures(file, kmer_size=31)[0] for file in sample_files]

    nwk = cluster_signatures(signatures=signature_obj, method=cluster_method)

    # test that a longer string was returned
    assert nwk is not None and len(nwk) > 0


def test_cluster_single_signatures(data_dir: Path):
    """Test clustering only a single."""
    signature = get_data_path(data_dir, "DRR237260.sig")

    signature_obj = read_signatures(signature, kmer_size=31)

    with pytest.raises(ValueError):
        cluster_signatures(signatures=[signature_obj], method=ClusterMethod.SINGLE)
