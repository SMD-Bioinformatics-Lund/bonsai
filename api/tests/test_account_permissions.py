"""Exercise route scopes without executing analysis or curation work."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.security import SecurityScopes
from fastapi.testclient import TestClient

from bonsai_api.config import USER_ROLES
from bonsai_api.dependencies import get_current_user, get_database, get_audit_log, get_request_context
from bonsai_api.routers.samples import samples
from bonsai_api.routers import analysis


@pytest.mark.parametrize("role", ["user", "uploader", "admin"])
def test_generic_record_creation_uses_the_configured_write_role(role,monkeypatch):
    async def user(security_scopes:SecurityScopes):
        if not set(security_scopes.scopes)<=set(USER_ROLES[role]):raise HTTPException(401)
        return SimpleNamespace(username=role,roles=[role],disabled=False)
    create=AsyncMock(return_value={"internal_sample_id":"generic-owned"})
    monkeypatch.setattr(samples,"create_sample_service",create)
    app=FastAPI();app.include_router(samples.router)
    app.dependency_overrides[get_current_user]=user
    app.dependency_overrides[get_database]=lambda:None
    app.dependency_overrides[get_audit_log]=lambda:None
    app.dependency_overrides[get_request_context]=lambda:None
    with TestClient(app) as client:response=client.post('/samples/',json={"sample_id":"generic-owned","sample_name":"Generic record"})
    allowed=role in {"uploader","admin"}
    assert response.status_code==(201 if allowed else 401)
    assert create.await_count==int(allowed)


def test_write_only_role_cannot_read_saved_curation_records(monkeypatch):
    async def user(security_scopes:SecurityScopes):
        if not set(security_scopes.scopes)<=set(USER_ROLES['uploader']):raise HTTPException(401)
        return SimpleNamespace(username='uploader',roles=['uploader'],disabled=False)
    read=AsyncMock(return_value=[])
    monkeypatch.setattr(analysis,'get_curations_service',read)
    app=FastAPI();app.include_router(analysis.router)
    app.dependency_overrides[get_current_user]=user
    app.dependency_overrides[get_database]=lambda:None
    with TestClient(app) as client:response=client.get('/analysis/not-a-real-analysis/curations')
    assert response.status_code==401
    read.assert_not_awaited()
