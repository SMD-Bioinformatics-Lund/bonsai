"""The curation edit API accepts annotations but never identity or audit fields."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bonsai_api.routers import analysis
from bonsai_api.dependencies import get_database, get_current_active_user, get_request_context, get_audit_log


@pytest.fixture
def curation_client(monkeypatch):
    app = FastAPI()
    app.include_router(analysis.router)
    for dependency, value in (
        (get_database, SimpleNamespace()),
        (get_current_active_user, SimpleNamespace(username="user")),
        (get_request_context, SimpleNamespace()),
        (get_audit_log, None),
    ):
        app.dependency_overrides[dependency] = lambda value=value: value
    save = AsyncMock()
    monkeypatch.setattr(analysis, "update_variant_curation_service", save)
    with TestClient(app) as client:
        yield client, save


def test_edit_routes_to_update_service_with_authenticated_user(curation_client):
    client, save = curation_client
    response = client.put("/analysis/curations/existing", json={
        "decision": "accept", "phenotypes": [{"name": "rifampicin"}],
    })
    assert response.status_code == 200
    assert response.json() == {"curation_id": "existing"}
    assert save.await_args.kwargs["curated_by"] == "user"
    assert save.await_args.kwargs["curation_id"] == "existing"
    assert save.await_args.kwargs["curation"].phenotypes[0].name == "rifampicin"


@pytest.mark.parametrize("extra", [
    {"id": "other"}, {"analysis_id": "other"}, {"result_key": "other"},
    {"annotation_type": "gene"}, {"curated_by": "other-user"}, {"approved_by": "other-user"},
    {"decision": "invalid"}, {"phenotypes": None},
])
def test_edit_rejects_invalid_annotations_and_identity_changes(curation_client, extra):
    client, save = curation_client
    response = client.put("/analysis/curations/existing", json={"decision": "accept", **extra})
    assert response.status_code == 422
    save.assert_not_awaited()
