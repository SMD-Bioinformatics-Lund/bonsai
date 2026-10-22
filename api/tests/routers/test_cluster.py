"""MinHash clustering rejects incomplete selections before scheduling work."""

import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from bonsai_api.dependencies import get_database
from bonsai_api.internal.error_handlers import register_exception_handlers
from bonsai_api.redis import minhash
from bonsai_api.routers.cluster import router


@pytest.fixture()
def cluster_client(monkeypatch):
    samples = AsyncMongoMockClient().bonsai.samples
    db = SimpleNamespace(sample_collection=samples)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_database] = lambda: db
    register_exception_handlers(app)
    enqueue = Mock(return_value=SimpleNamespace(id="cluster-job"))
    monkeypatch.setattr(minhash, "enqueue_job", enqueue)
    with TestClient(app) as client:
        yield client, samples, enqueue


@pytest.mark.parametrize("signature_state", ["null", "empty", "absent", "unknown"])
def test_minhash_clustering_rejects_any_missing_signature(
    cluster_client, signature_state
):
    client, samples, enqueue = cluster_client
    records = [
        {"sample_id": "good-a", "genome_signature": "upload-a"},
        {"sample_id": "good-b", "genome_signature": "upload-b"},
    ]
    bad = {"sample_id": "bad", "external_sample_id": "LAB-123"}
    if signature_state == "null":
        bad["genome_signature"] = None
    elif signature_state == "empty":
        bad["genome_signature"] = ""
    if signature_state != "unknown":
        records.append(bad)
    asyncio.run(samples.insert_many(records))

    response = client.post(
        "/cluster/minhash",
        json={"sampleIds": ["good-a", "bad", "good-b"], "method": "single"},
    )

    assert response.status_code == 404
    label = "bad" if signature_state == "unknown" else "LAB-123"
    assert response.json()["detail"] == (
        f"No MinHash signature is available for the following samples: {label}"
    )
    enqueue.assert_not_called()


def test_minhash_clustering_reports_all_missing_samples(cluster_client):
    client, samples, enqueue = cluster_client
    asyncio.run(
        samples.insert_many(
            [
                {"sample_id": "missing-a", "external_sample_id": "LAB-A"},
                {"sample_id": "missing-b", "external_sample_id": "LAB-B"},
            ]
        )
    )

    response = client.post(
        "/cluster/minhash",
        json={"sampleIds": ["missing-b", "unknown", "missing-a"], "method": "single"},
    )

    assert response.status_code == 404
    assert response.json()["detail"].endswith("LAB-A, LAB-B, unknown")
    enqueue.assert_not_called()


def test_minhash_clustering_passes_labels_and_unique_ids_to_worker(cluster_client):
    client, samples, enqueue = cluster_client
    # Database order differs from selection order. Labels never replace tree IDs.
    asyncio.run(
        samples.insert_many(
            [
                {
                    "sample_id": "sample-b",
                    "genome_signature": "upload-b",
                    "external_sample_id": "",
                },
                {
                    "sample_id": "sample-a",
                    "genome_signature": "upload-a",
                    "external_sample_id": "LAB-A",
                },
            ]
        )
    )

    response = client.post(
        "/cluster/minhash",
        json={"sampleIds": ["sample-a", "sample-b", "sample-a"], "method": "single"},
    )

    assert response.status_code == 201
    assert response.json()["id"] == "cluster-job"
    queued = enqueue.call_args.kwargs
    assert queued["sample_ids"] == ["sample-a", "sample-b"]
    assert queued["sample_labels"] == {"sample-a": "LAB-A", "sample-b": "sample-b"}
    assert queued["cluster_method"] == "single"


def test_minhash_clustering_requires_two_distinct_samples(cluster_client):
    client, _, enqueue = cluster_client

    response = client.post(
        "/cluster/minhash",
        json={"sampleIds": ["only", "only"], "method": "single"},
    )

    assert response.status_code == 422
    assert "at least two distinct samples" in response.json()["detail"]
    enqueue.assert_not_called()
