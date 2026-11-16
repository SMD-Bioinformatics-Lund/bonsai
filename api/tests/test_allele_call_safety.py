"""Strict inputs and explicit sample accounting before allele jobs are queued."""

import asyncio
import csv
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bonsai_api.crud.cluster import TypingProfileAggregate, get_typing_profiles
from bonsai_api.dependencies import get_database
from bonsai_api.exceptions import InvalidDataFormat
from bonsai_api.internal.error_handlers import register_exception_handlers
from bonsai_api.redis import allele_cluster
from bonsai_api.redis.models import MsTreeMethods, SubmittedJob
from bonsai_api.routers import cluster as routes


def database(rows):
    async def records():
        for row in rows:
            yield row

    return SimpleNamespace(
        sample_collection=SimpleNamespace(aggregate=AsyncMock(return_value=records()))
    )


def sample(sid, calls):
    return {"sample_id": sid, "external_sample_id": f"LAB-{sid}", "typing_result": calls}


def endpoint(monkeypatch, rows):
    db = database(rows)
    app = FastAPI()
    app.include_router(routes.router)
    register_exception_handlers(app)
    app.dependency_overrides[get_database] = lambda: db
    schedule = Mock(return_value=SubmittedJob(id="job", task="cluster"))
    monkeypatch.setattr(routes, "schedule_allele_cluster_samples", schedule)
    return TestClient(app), schedule, db


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
@pytest.mark.parametrize("bad", [None, ["1", "2"], {}, 1.0, "INF"])
def test_invalid_calls_still_reject_the_submission(monkeypatch, method, bad):
    client, schedule, _ = endpoint(
        monkeypatch, [sample("a", {"x": bad, "y": 1}), sample("b", {"x": 1, "y": 1})]
    )
    response = client.post(
        f"/cluster/{method}", json={"sampleIds": ["a", "b"], "method": "MSTreeV2"}
    )
    assert response.status_code == 422
    assert response.json()["type"] == "urn:bonsai:problem:invalid-data"
    assert f"Invalid {method} allele call at x for LAB-a" in response.json()["detail"]
    assert "samples" not in response.json()
    schedule.assert_not_called()


def test_malformed_profile_still_rejects():
    with pytest.raises(InvalidDataFormat, match="Invalid mlst allele profile for LAB-a"):
        asyncio.run(get_typing_profiles(database([sample("a", ["bad"])]), ["a"], "mlst"))


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_all_uncallable_samples_are_reported_without_enqueuing(monkeypatch, method):
    client, schedule, _ = endpoint(monkeypatch, [
        sample("a", {"x": 0, "y": "LNF"}),
        sample("b", {"x": 1, "y": 2}),
        sample("c", {"x": "0", "y": "ASM"}),
    ])
    response = client.post(
        f"/cluster/{method}", json={"sampleIds": ["a", "b", "c"], "method": "MSTreeV2"}
    )
    assert response.status_code == 422
    problem = response.json()
    assert problem["type"] == "urn:bonsai:problem:no-usable-allele-calls"
    assert problem["typing_method"] == method
    assert problem["samples"] == [
        {"sample_id": "a", "label": "LAB-a"},
        {"sample_id": "c", "label": "LAB-c"},
    ]
    schedule.assert_not_called()


def test_metadata_columns_cannot_make_a_sample_callable(monkeypatch):
    client, schedule, _ = endpoint(monkeypatch, [
        sample("a", {"ST": 10, "#note": 3, "x": "LNF"}),
        sample("b", {"x": 1}),
    ])
    response = client.post("/cluster/mlst", json={"sampleIds": ["a", "b"], "method": "MSTreeV2"})
    assert response.status_code == 422
    assert response.json()["samples"] == [{"sample_id": "a", "label": "LAB-a"}]
    schedule.assert_not_called()


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_existing_missing_markers_allow_a_partially_callable_profile(monkeypatch, method):
    client, schedule, db = endpoint(monkeypatch, [
        sample("a", {"x": "LNF", "y": 0, "z": 2}),
        sample("b", {"x": 1, "y": "0", "z": "2"}),
    ])
    response = client.post(
        f"/cluster/{method}", json={"sampleIds": ["a", "b"], "method": "MSTreeV2"}
    )
    assert response.status_code == 201
    db.sample_collection.aggregate.assert_awaited_once()
    profiles = schedule.call_args.args[0]
    assert [p.sample_id for p in profiles] == ["a", "b"]
    assert profiles[0].allele_profile() == {"x": None, "y": 0, "z": 2}


def test_tsv_preserves_integer_calls_and_the_sample_id_header(monkeypatch):
    enqueue = Mock(return_value=SimpleNamespace(id="job", worker_name="worker"))
    monkeypatch.setattr(allele_cluster, "redis", SimpleNamespace(allele=SimpleNamespace(enqueue=enqueue)))
    # None here is produced internally from accepted error markers, not raw input.
    profiles = [
        TypingProfileAggregate(sample_id="a", typing_result={"x": 0, "y": 1}),
        TypingProfileAggregate(sample_id="b", typing_result={"x": 2, "y": 1}),
        TypingProfileAggregate(sample_id="c", typing_result={"x": None, "y": 1}),
    ]
    allele_cluster.schedule_cluster_samples(profiles, MsTreeMethods.MSTREE_V2)
    rows = list(csv.reader(io.StringIO(enqueue.call_args.kwargs["profile"]), delimiter="\t"))
    assert rows == [["sample_id", "x", "y"], ["a", "0", "1"], ["b", "2", "1"], ["c", "-", "1"]]
