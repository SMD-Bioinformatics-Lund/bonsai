"""Never silently lose allele columns or sample identities."""

import copy
import tempfile

import numpy as np
import pytest
from ete3 import Tree

from allele_cluster_service import ms_trees, tasks


@pytest.fixture
def worker(monkeypatch, tmp_path):
    params = copy.deepcopy(ms_trees.params)
    params.update(
        method="MSTreeV2",
        matrix_type="asymmetric",
        heuristic="harmonic",
        branch_recraft=True,
        n_proc=1,
    )
    monkeypatch.setattr(ms_trees, "params", params)
    original_tempfile = tempfile.NamedTemporaryFile

    def local_tempfile(*args, **kwargs):
        kwargs["dir"] = str(tmp_path)
        return original_tempfile(*args, **kwargs)

    monkeypatch.setattr(ms_trees.tempfile, "NamedTemporaryFile", local_tempfile)
    return tasks.cluster


@pytest.mark.parametrize("header", ["sample_id\tg1\tg2\tg3", "\tg1\tg2\tg3"])
def test_last_locus_is_compared_even_with_legacy_blank_index_header(worker, header):
    result = worker(header + "\na\t1\t1\t1\nb\t1\t1\t2\n", "MSTreeV2")
    assert Tree(result).get_distance("a", "b") == 1


def test_all_missing_sample_is_rejected_instead_of_disappearing(worker):
    with pytest.raises(ValueError, match="no usable allele calls.*empty"):
        worker("sample_id\tx\ty\na\t1\t1\nb\t2\t1\nempty\t-\t-\n", "MSTreeV2")


def test_legacy_zero_float_is_a_missing_call():
    names, profiles, _ = ms_trees.nonredundant(
        np.array(["a", "b"]), np.array([["0.0", "1"], ["1.0", "1"]])
    )
    assert profiles[list(names).index("a"), 0] == 0


def test_expected_sample_ids_guard_against_partial_worker_results(monkeypatch):
    monkeypatch.setattr(tasks, "backend", lambda **_: "(a:0);")
    with pytest.raises(ValueError, match="every expected sample"):
        tasks.cluster("sample_id\tx\na\t1\nb\t2\n", "MSTreeV2", ["a", "b"])


def test_one_placeable_sample_is_retained_without_inventing_other_positions(worker):
    newick = worker("sample_id\tx\na\t1\n", "MSTreeV2", ["a"])
    assert Tree(newick).get_leaf_names() == ["a"]


def test_identical_profiles_retain_every_expected_sample(worker):
    newick = worker("sample_id\tx\na\t1\nb\t1\n", "MSTreeV2", ["a", "b"])
    assert sorted(Tree(newick).get_leaf_names()) == ["a", "b"]


def test_empty_or_incomplete_tables_fail_clearly(worker):
    for profile in ["sample_id\na\n", "sample_id\tx\ty\na\t1\n"]:
        with pytest.raises(ValueError, match="No allele columns|Incomplete allele row"):
            worker(profile, "MSTreeV2", ["a"])
