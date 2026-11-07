"""Regressions from the bounded record-management pass; no analyses are run."""

from contextlib import asynccontextmanager
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.security import SecurityScopes
from fastapi.testclient import TestClient

from bonsai_api.config import USER_ROLES
from bonsai_api.dependencies import get_audit_log, get_current_user, get_database, get_request_context
from bonsai_api.io import parse_metadata_table
from bonsai_api.models.metadata import InputTableMetadata, TableMetadataInDb
from bonsai_api.routers.samples import samples as sample_routes
from bonsai_api.routers.samples import sample_metadata as metadata_routes
from bonsai_api.crud import metadata as metadata_crud
from bonsai_api.dependencies import get_current_active_user


def test_csv_empty_cells_remain_json_serializable():
    table = parse_metadata_table(InputTableMetadata(fieldname="Inventory", value="Item,Count\nDesk,\nChair,3\n"))
    assert table.data[0] == ["Desk", ""]
    json.dumps(table.model_dump(mode="json"), allow_nan=False)


def test_legacy_stored_missing_cells_remain_readable():
    table = TableMetadataInDb(fieldname="Inventory", category="general", columns=["Item", "Count"],
                               data=[["Desk", float("nan")], ["Chair", None]])
    assert table.data == [["Desk", ""], ["Chair", ""]]
    json.dumps(table.model_dump(mode="json"), allow_nan=False)


def test_nonfinite_stored_numbers_have_a_json_representation():
    table = TableMetadataInDb(fieldname="Numbers", category="general", data=[[float("inf"), float("-inf")]])
    assert table.data == [["inf", "-inf"]]
    json.dumps(table.model_dump(mode="json"), allow_nan=False)


@pytest.mark.parametrize("role,status_code", [("user", 401), ("admin", 200)])
def test_record_deletion_requires_write_permission(monkeypatch, role, status_code):
    @asynccontextmanager
    async def transaction(*args, **kwargs):
        yield None

    async def current_user(security_scopes: SecurityScopes):
        if not set(security_scopes.scopes) <= set(USER_ROLES[role]):
            raise HTTPException(401, "Insufficient permissions")
        return SimpleNamespace(username=role, disabled=False, roles=[role])

    delete = AsyncMock(return_value=None)
    monkeypatch.setattr(sample_routes, "managed_transaction", transaction)
    monkeypatch.setattr(sample_routes, "check_samples_exists", AsyncMock(return_value=[]))
    monkeypatch.setattr(sample_routes, "delete_sample_service", delete)
    app = FastAPI()
    app.include_router(sample_routes.router)
    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_database] = lambda: SimpleNamespace(client=None)
    app.dependency_overrides[get_audit_log] = lambda: None
    app.dependency_overrides[get_request_context] = lambda: SimpleNamespace(actor=None, metadata=None)
    with TestClient(app) as client:
        response = client.request("DELETE", "/samples/", json=["bounded-test-record"])
    assert response.status_code == status_code
    assert delete.await_count == (1 if role == "admin" else 0)


@pytest.mark.parametrize("data", [[], [{"fieldname": "Invalid", "type": "table", "value": 'Item,Count\n"unclosed,2'}]])
def test_invalid_metadata_is_rejected_without_a_database_write(monkeypatch, data):
    monkeypatch.setattr(metadata_crud, "get_sample_by_id", AsyncMock(return_value={"metadata": []}))
    update = AsyncMock(return_value=SimpleNamespace(matched_count=1, modified_count=0))
    app = FastAPI()
    app.include_router(metadata_routes.router)
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(username="admin")
    app.dependency_overrides[get_database] = lambda: SimpleNamespace(sample_collection=SimpleNamespace(update_one=update))
    with TestClient(app) as client:
        response = client.post("/samples/bounded-record/metadata", json=data)
    assert response.status_code == 422
    update.assert_not_awaited()
