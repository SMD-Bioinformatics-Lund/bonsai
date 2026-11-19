"""Every allele column must contribute to the calculated distance."""

import copy
import tempfile

import pytest
from ete3 import Tree

from allele_cluster_service import ms_trees
from allele_cluster_service.tasks import cluster


@pytest.fixture(autouse=True)
def worker_settings(monkeypatch, tmp_path):
    params = copy.deepcopy(ms_trees.params)
    params["n_proc"] = 1
    monkeypatch.setattr(ms_trees, "params", params)
    original = tempfile.NamedTemporaryFile

    def local_tempfile(*args, **kwargs):
        kwargs["dir"] = str(tmp_path)
        return original(*args, **kwargs)

    monkeypatch.setattr(ms_trees.tempfile, "NamedTemporaryFile", local_tempfile)


@pytest.mark.parametrize("sample_header", ["", "sample_id", "#sample_id"])
@pytest.mark.parametrize("changed_locus", range(7))
def test_every_locus_changes_the_distance(sample_header, changed_locus):
    alleles = ["1"] * 7
    changed = list(alleles)
    changed[changed_locus] = "2"
    profile = "\t".join([sample_header, *[f"locus{i}" for i in range(7)]]) + "\r\n"
    profile += "\t".join(["a", *alleles]) + "\r\n"
    profile += "\t".join(["b", *changed]) + "\r\n"
    assert Tree(cluster(profile, "MSTreeV2")).get_distance("a", "b") == 1
