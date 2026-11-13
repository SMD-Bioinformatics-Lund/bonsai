"""Browser validation and authoritative submission enforce the same scheme rules."""

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
    getter = AsyncMock(
        return_value=[
            TypingProfileAggregate(sample_id=sid, scheme="same", typing_result={"x": 1})
            for sid in ["a", "b"]
        ]
    )
    schedule = Mock(return_value=SubmittedJob(id="job", task="cluster"))
    monkeypatch.setattr(routes, "get_typing_profiles", getter)
    monkeypatch.setattr(routes, "schedule_allele_cluster_samples", schedule)
    return TestClient(app), getter, schedule


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_direct_submission_cannot_bypass_scheme_checks(endpoint, method):
    client, getter, schedule = endpoint
    getter.return_value[1].scheme = "other"
    response = client.post(
        f"/cluster/{method}", json={"sampleIds": ["a", "b"], "method": "MSTreeV2"}
    )
    assert response.status_code == 422
    assert "different typing schemes" in response.json()["detail"]
    getter.assert_awaited_once()
    schedule.assert_not_called()


def test_static_preflight_route_checks_both_methods(endpoint):
    client, getter, schedule = endpoint
    incompatible = [
        TypingProfileAggregate(sample_id=sid, scheme=sid, typing_result={"x": 1})
        for sid in ["a", "b"]
    ]
    compatible = getter.return_value
    getter.side_effect = [incompatible, compatible]
    response = client.post("/cluster/validate", json={"sampleIds": ["a", "b"]})
    assert response.status_code == 200
    assert response.json()["mlst"]["can_cluster"] is False
    assert response.json()["cgmlst"]["can_cluster"] is True
    assert [call.args[-1] for call in getter.await_args_list] == ["mlst", "cgmlst"]
    schedule.assert_not_called()


def test_compatible_profiles_are_validated_from_the_same_read_as_submission(endpoint):
    client, getter, schedule = endpoint
    response = client.post(
        "/cluster/mlst", json={"sampleIds": ["a", "b"], "method": "MSTreeV2"}
    )
    assert response.status_code == 201
    getter.assert_awaited_once()
    assert schedule.call_args.args[0] is getter.return_value


def test_unavailable_method_does_not_hide_other_preflight_results(endpoint):
    from bonsai_api.exceptions import EntryNotFound

    client, getter, _ = endpoint
    getter.side_effect = [EntryNotFound("No MLST profiles"), getter.return_value]
    response = client.post("/cluster/validate", json={"sampleIds": ["a", "b"]})
    assert response.status_code == 200
    assert response.json()["mlst"]["can_cluster"] is False
    assert response.json()["cgmlst"]["can_cluster"] is True
