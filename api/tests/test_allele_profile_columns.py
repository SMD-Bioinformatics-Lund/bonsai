"""Exercise the API export and the real allele worker together."""

import copy
import csv
import io
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bonsai_api.crud.cluster import TypingProfileAggregate
from bonsai_api.redis import allele_cluster
from bonsai_api.redis.models import MsTreeMethods


def test_export_and_worker_preserve_all_loci(monkeypatch, tmp_path):
    worker = pytest.importorskip("allele_cluster_service.tasks")
    from allele_cluster_service import ms_trees
    from ete3 import Tree

    params = copy.deepcopy(ms_trees.params)
    params["n_proc"] = 1
    monkeypatch.setattr(ms_trees, "params", params)
    original = tempfile.NamedTemporaryFile

    def local_tempfile(*args, **kwargs):
        kwargs["dir"] = str(tmp_path)
        return original(*args, **kwargs)

    monkeypatch.setattr(ms_trees.tempfile, "NamedTemporaryFile", local_tempfile)
    enqueue = Mock(return_value=SimpleNamespace(id="job", worker_name="worker"))
    monkeypatch.setattr(
        allele_cluster,
        "redis",
        SimpleNamespace(allele=SimpleNamespace(enqueue=enqueue)),
    )
    calls = {**{f"gene{i}": 1 for i in range(7)}, "ST": 1, "#locus": 1}
    for gene in calls:
        changed = dict(calls)
        changed[gene] = 2
        allele_cluster.schedule_cluster_samples(
            [
                TypingProfileAggregate(sample_id="a", typing_result=calls),
                TypingProfileAggregate(sample_id="b", typing_result=changed),
            ],
            MsTreeMethods.MSTREE_V2,
        )
        queued = enqueue.call_args.kwargs
        rows = list(csv.reader(io.StringIO(queued["profile"]), delimiter="\t"))
        assert rows[0] == ["sample_id", *[f"allele:{locus}" for locus in calls]]
        assert all(len(row) == len(calls) + 1 for row in rows)
        tree = Tree(worker.cluster(queued["profile"], queued["method"]))
        assert tree.get_distance("a", "b") == 1
