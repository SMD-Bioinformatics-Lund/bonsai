"""Allele TSV export must preserve integers in columns containing missing calls."""

import csv
import io
from types import SimpleNamespace
from unittest.mock import Mock

from bonsai_api.crud.cluster import TypingProfileAggregate
from bonsai_api.redis import allele_cluster
from bonsai_api.redis.models import MsTreeMethods


def test_tsv_preserves_integer_calls_with_missing_values(monkeypatch):
    enqueue = Mock(return_value=SimpleNamespace(id="job", worker_name="worker"))
    monkeypatch.setattr(
        allele_cluster,
        "redis",
        SimpleNamespace(allele=SimpleNamespace(enqueue=enqueue)),
    )
    profiles = [
        TypingProfileAggregate(sample_id="a", typing_result={"x": 0, "y": 1}),
        TypingProfileAggregate(sample_id="b", typing_result={"x": 2, "y": 1}),
        TypingProfileAggregate(sample_id="c", typing_result={"x": None, "y": 1}),
    ]
    allele_cluster.schedule_cluster_samples(profiles, MsTreeMethods.MSTREE_V2)

    rows = list(
        csv.reader(io.StringIO(enqueue.call_args.kwargs["profile"]), delimiter="\t")
    )
    assert rows == [
        ["sample_id", "x", "y"],
        ["a", "0", "1"],
        ["b", "2", "1"],
        ["c", "-", "1"],
    ]
