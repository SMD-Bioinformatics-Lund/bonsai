"""Failed QC is an actionable MinHash conflict, before a worker job is queued."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import mongomock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bonsai_api.dependencies import get_database
from bonsai_api.redis.models import SubmittedJob
from bonsai_api.routers import cluster


def setup_client(monkeypatch, samples):
    collection = mongomock.MongoClient().db.samples
    collection.insert_many(samples)
    # Run the actual filter and projection, exposing the async database interface.
    find = Mock(
        side_effect=lambda query, projection: SimpleNamespace(
            to_list=AsyncMock(return_value=list(collection.find(query, projection)))
        )
    )
    db = SimpleNamespace(sample_collection=SimpleNamespace(find=find))
    schedule = Mock(return_value=SubmittedJob(id="job-1", task="cluster_samples"))
    monkeypatch.setattr(cluster, "schedule_minhash_cluster_samples", schedule)
    app = FastAPI()
    app.include_router(cluster.router)
    app.dependency_overrides[get_database] = lambda: db
    return TestClient(app), schedule, collection


@pytest.mark.parametrize("count", [1, 2])
def test_failed_qc_returns_exact_ids_without_queuing_or_modifying_samples(
    monkeypatch, count
):
    failed = [
        {"sample_id": f"failed-{i}", "qc_status": {"status": "failed"}}
        for i in range(count)
    ]
    samples = failed + [
        {"sample_id": "passed", "qc_status": {"status": "passed"}},
        {"sample_id": "unselected-failed", "qc_status": {"status": "failed"}},
    ]
    client, schedule, collection = setup_client(monkeypatch, samples)
    before = list(collection.find())
    failed_ids = [sample["sample_id"] for sample in reversed(failed)]
    response = client.post(
        "/cluster/minhash",
        json={
            "sampleIds": ["passed", *failed_ids, failed_ids[0]],
            "method": "single",
        },
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "minhash_qc_failed"
    assert detail["sample_ids"] == failed_ids
    assert "failed QC" in detail["message"]
    assert (
        f"{count} {'sample has' if count == 1 else 'samples have'}" in detail["message"]
    )
    schedule.assert_not_called()
    assert list(collection.find()) == before


def test_passed_unprocessed_and_missing_qc_do_not_get_classified_as_failed(monkeypatch):
    samples = [
        {"sample_id": "passed", "qc_status": {"status": "passed"}},
        {"sample_id": "unprocessed", "qc_status": {"status": "unprocessed"}},
        {"sample_id": "unknown", "qc_status": None},
        {"sample_id": "legacy"},
    ]
    client, schedule, _ = setup_client(monkeypatch, samples)
    sample_ids = [sample["sample_id"] for sample in samples] + ["missing"]
    response = client.post(
        "/cluster/minhash",
        json={
            "sampleIds": sample_ids,
            "method": "single",
        },
    )
    assert response.status_code == 201
    assert response.json()["id"] == "job-1"
    # Signature-data validation still belongs to the worker, including missing samples.
    assert schedule.call_args.args[0] == sample_ids


def test_failed_qc_does_not_change_other_clustering_methods(monkeypatch):
    client, minhash_schedule, _ = setup_client(
        monkeypatch,
        [
            {"sample_id": "failed", "qc_status": {"status": "failed"}},
            {"sample_id": "passed", "qc_status": {"status": "passed"}},
        ],
    )
    profiles = AsyncMock(return_value=[])
    schedule = Mock(return_value=SubmittedJob(id="mlst-job", task="cluster_samples"))
    monkeypatch.setattr(cluster, "get_typing_profiles", profiles)
    monkeypatch.setattr(cluster, "schedule_allele_cluster_samples", schedule)
    response = client.post(
        "/cluster/mlst",
        json={
            "sampleIds": ["failed", "passed"],
            "method": "MSTreeV2",
        },
    )
    assert response.status_code == 201
    minhash_schedule.assert_not_called()
    profiles.assert_awaited_once()
    schedule.assert_called_once()
