"""Missing markers must not become real calls or silently remove samples."""

import numpy as np
import pytest

from allele_cluster_service import ms_trees


@pytest.mark.parametrize("missing", ["0", "0.0", "-", "N", ""])
def test_missing_markers_are_encoded_as_missing(missing):
    names, profiles, _ = ms_trees.nonredundant(
        np.array(["a", "b"]), np.array([[missing, "1"], ["2", "1"]])
    )
    assert profiles[list(names).index("a"), 0] == 0
    assert profiles[list(names).index("b"), 0] > 0


@pytest.mark.parametrize("missing", ["0", "0.0", "-", "N", ""])
def test_uncallable_samples_fail_instead_of_disappearing(missing):
    with pytest.raises(ValueError, match="no usable allele calls: empty"):
        ms_trees.nonredundant(
            np.array(["good", "empty"]), np.array([["1", "1"], [missing, "-"]])
        )


def test_no_allele_columns_fail_explicitly():
    with pytest.raises(ValueError, match="No allele columns"):
        ms_trees.nonredundant(np.array(["a", "b"]), np.empty((2, 0), dtype=str))
