"""A sample is placed exactly once or explicitly retained as unplaced."""

import asyncio
import csv
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from ete3 import Tree

from bonsai_api.crud.cluster import TypingProfileAggregate, get_typing_profiles
from bonsai_api.exceptions import EntryNotFound, InvalidDataFormat
from bonsai_api.redis import allele_cluster
from bonsai_api.redis.models import MsTreeMethods


def profile(sample_id, calls, label=None):
    return TypingProfileAggregate(sample_id=sample_id, label=label, typing_result=calls)


@pytest.fixture
def enqueue(monkeypatch):
    enqueue = Mock(return_value=SimpleNamespace(id="job", worker_name="worker"))
    monkeypatch.setattr(
        allele_cluster,
        "redis",
        SimpleNamespace(allele=SimpleNamespace(enqueue=enqueue)),
    )
    return enqueue


def test_queued_tree_and_unplaced_list_account_for_every_selected_sample(enqueue):
    selected = [
        profile("a", {"x": 1, "y": 2}),
        profile("empty", {"x": "LNF", "y": 0}, "LAB-EMPTY"),
        profile("absent", {}, "LAB-ABSENT"),
    ]
    allele_cluster.schedule_cluster_samples(selected, MsTreeMethods.MSTREE_V2)
    queued = enqueue.call_args.kwargs
    assert queued["sample_ids"] == ["a"]
    assert queued["meta"]["unplaced_samples"] == [
        {
            "sample_id": sid,
            "label": label,
            "reason": "No usable allele calls are available.",
        }
        for sid, label in [("empty", "LAB-EMPTY"), ("absent", "LAB-ABSENT")]
    ]
    rows = list(csv.reader(io.StringIO(queued["profile"]), delimiter="\t"))
    assert [row[0] for row in rows[1:]] == ["a"]
    worker = pytest.importorskip("allele_cluster_service.tasks")
    assert Tree(
        worker.cluster(queued["profile"], queued["method"], queued["sample_ids"])
    ).get_leaf_names() == ["a"]


def test_selection_without_usable_samples_is_rejected_without_enqueuing(enqueue):
    with pytest.raises(
        InvalidDataFormat, match="No selected sample has usable allele calls"
    ):
        allele_cluster.schedule_cluster_samples(
            [profile("a", {"x": 0}), profile("b", {})], MsTreeMethods.MSTREE_V2
        )
    enqueue.assert_not_called()


def test_missing_database_sample_is_still_rejected():
    async def records():
        if False:
            yield

    db = SimpleNamespace(
        sample_collection=SimpleNamespace(aggregate=AsyncMock(return_value=records()))
    )
    with pytest.raises(EntryNotFound):
        asyncio.run(get_typing_profiles(db, ["missing"], "mlst"))
