"""Float-formatted zeroes must retain the existing missing-call semantics."""

import numpy as np
import pytest

from allele_cluster_service import ms_trees


@pytest.mark.parametrize("missing", ["0", "0.0", "-", "N"])
def test_missing_markers_are_encoded_as_missing(missing):
    names, profiles, _ = ms_trees.nonredundant(
        np.array(["a", "b"]), np.array([[missing, "1"], ["2", "1"]])
    )
    assert profiles[list(names).index("a"), 0] == 0
    assert profiles[list(names).index("b"), 0] > 0
