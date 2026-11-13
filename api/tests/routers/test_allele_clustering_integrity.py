"""The API independently enforces the UI's scheme checks."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from bonsai_api.crud.cluster import TypingProfileAggregate
from bonsai_api.dependencies import get_database
from bonsai_api.internal.error_handlers import register_exception_handlers
from bonsai_api.redis.models import SubmittedJob
from bonsai_api.routers import cluster as routes


@pytest.fixture
def endpoint(monkeypatch):
    app = FastAPI()
    app.include_router(routes.router)
    register_exception_handlers(app)
    app.dependency_overrides[get_database] = lambda: SimpleNamespace()
    getter = AsyncMock()
    schedule = Mock(return_value=SubmittedJob(id="job", task="cluster"))
    monkeypatch.setattr(routes, "get_typing_profiles", getter)
    monkeypatch.setattr(routes, "schedule_allele_cluster_samples", schedule)
    return TestClient(app), getter, schedule


def profiles(schemes):
    return [
        TypingProfileAggregate(sample_id=sample, typing_result={"x": 1}, scheme=scheme)
        for sample, scheme in zip(["a", "b"], schemes)
    ]


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_incompatible_schemes_cannot_bypass_the_browser(endpoint, method):
    client, getter, schedule = endpoint
    getter.return_value = profiles(["scheme-a", "scheme-b"])
    response = client.post(
        f"/cluster/{method}", json={"sampleIds": ["a", "b"], "method": "MSTreeV2"}
    )
    assert response.status_code == 422
    assert "different typing schemes" in response.json()["detail"]
    schedule.assert_not_called()


def test_validation_route_is_reachable_and_uses_same_rules(endpoint):
    client, getter, schedule = endpoint
    getter.side_effect = [profiles(["a", "b"]), profiles(["same", "same"])]
    response = client.post("/cluster/validate", json={"sampleIds": ["a", "b"]})
    assert response.status_code == 200
    assert response.json()["mlst"]["can_cluster"] is False
    assert response.json()["cgmlst"]["can_cluster"] is True
    schedule.assert_not_called()


def test_only_unplaced_profiles_do_not_enqueue_an_empty_tree(endpoint):
    client, getter, schedule = endpoint
    getter.return_value = [
        TypingProfileAggregate(sample_id=sid, typing_result={}) for sid in ["a", "b"]
    ]
    response = client.post(
        "/cluster/mlst", json={"sampleIds": ["a", "b"], "method": "MSTreeV2"}
    )
    assert response.status_code == 422
    assert "no selected sample has usable allele calls" in response.json()["detail"]
    schedule.assert_not_called()
