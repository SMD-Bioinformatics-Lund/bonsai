"""Missing markers must not become real allele identities."""

import copy
import tempfile

import numpy as np
import pytest

from ete3 import Tree

from allele_cluster_service import ms_trees, tasks


@pytest.mark.parametrize("missing", ["0", "0.0", "-", "N", ""])
def test_missing_markers_encode_as_missing(missing):
    names, profiles, _ = ms_trees.nonredundant(
        np.array(["a", "b"]), np.array([[missing, "1"], ["2", "1"]])
    )
    assert profiles[list(names).index("a"), 0] == 0
    assert profiles[list(names).index("b"), 0] > 0


def test_null_acceptance_cannot_enable_silent_sample_loss():
    with pytest.raises(ValueError, match="no usable allele calls: empty"):
        ms_trees.nonredundant(
            np.array(["a", "empty"]), np.array([["1", "1"], ["0.0", "-"]])
        )


def test_trailing_empty_calls_remain_missing_in_the_reader(monkeypatch, tmp_path):
    params = copy.deepcopy(ms_trees.params)
    params["n_proc"] = 1
    monkeypatch.setattr(ms_trees, "params", params)
    original = tempfile.NamedTemporaryFile

    def local_tempfile(*args, **kwargs):
        kwargs["dir"] = str(tmp_path)
        return original(*args, **kwargs)

    monkeypatch.setattr(ms_trees.tempfile, "NamedTemporaryFile", local_tempfile)
    tree = Tree(tasks.cluster("sample_id\tx\ty\na\t1\t\nb\t1\t1\n", "MSTreeV2"))
    assert set(tree.get_leaf_names()) == {"a", "b"}
    assert tree.get_distance("a", "b") == 0
