"""The static availability route must precede the clustering method route."""

from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from bonsai_api.dependencies import get_current_active_user, get_database
from bonsai_api.models.enums import TypingMethod
from bonsai_api.routers import cluster


def test_cluster_methods_route_inspects_selection_without_scheduling(monkeypatch):
    query = AsyncMock(return_value=[TypingMethod.CGMLST])
    monkeypatch.setattr(cluster, "get_available_cluster_methods", query)
    schedule = AsyncMock(side_effect=AssertionError("Availability must not enqueue a job"))
    monkeypatch.setattr(cluster, "schedule_allele_cluster_samples", schedule)
    db = object()
    app = FastAPI()
    app.include_router(cluster.router)
    app.dependency_overrides[get_database] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: None

    response = TestClient(app).post("/cluster/methods", json={"sampleIds": ["a", "b"]})

    assert response.status_code == 200
    assert response.json() == {"methods": ["cgmlst"]}
    query.assert_awaited_once_with(db, ["a", "b"])
    schedule.assert_not_called()
