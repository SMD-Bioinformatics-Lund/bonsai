"""Worker jobs must contain all expected usable samples exactly once."""

from unittest.mock import Mock

import numpy as np
import pytest
from ete3 import Tree

from allele_cluster_service import ms_trees, tasks


def test_single_usable_sample_is_a_single_node_tree():
    assert Tree(
        tasks.cluster("\tgene\na\t1\n", "MSTreeV2", ["a"])
    ).get_leaf_names() == ["a"]


@pytest.mark.parametrize(
    "expected,table",
    [
        ([], "\tgene\na\t1\n"),
        (["a", "a"], "\tgene\na\t1\n"),
        (["a", "b"], "\tgene\na\t1\n"),
        (["a"], "\tgene\na\t1\nb\t1\n"),
        (["a"], "\tgene\na\t-\n"),
        (["a"], "\tgene\na\t0\n"),
        (["a"], "\tgene\na\t1\t2\n"),
    ],
)
def test_invalid_expected_sample_accounting_is_rejected(expected, table):
    with pytest.raises(ValueError):
        tasks.cluster(table, "MSTreeV2", expected)


@pytest.mark.parametrize("newick", ["(a:0);", "(a:0,a:0);", "(a:0,c:0);"])
def test_partial_or_incorrect_tree_is_rejected(monkeypatch, newick):
    backend = Mock(return_value=newick)
    monkeypatch.setattr(tasks, "backend", backend)
    with pytest.raises(ValueError, match="tree does not contain every expected sample"):
        tasks.cluster("\tx\ty\na\t1\t1\nb\t1\t2\n", "MSTreeV2", ["a", "b"])


def test_complete_tree_passes_accounting(monkeypatch):
    monkeypatch.setattr(tasks, "backend", lambda **_: "(a:0,b:1);")
    assert (
        tasks.cluster("\tx\ty\na\t1\t1\nb\t1\t2\n", "MSTreeV2", ["a", "b"])
        == "(a:0,b:1);"
    )


def test_legacy_worker_cannot_silently_drop_an_empty_sample():
    with pytest.raises(ValueError, match="no usable allele calls: empty"):
        ms_trees.nonredundant(
            np.array(["a", "empty"]), np.array([["1", "2"], ["0", "-"]])
        )
