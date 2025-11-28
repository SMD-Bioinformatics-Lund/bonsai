# tests/conftest.py
from __future__ import annotations

from uuid import uuid4

import mongomock
import pytest
from fastapi.testclient import TestClient

from audit_log_service.api import get_repo
from audit_log_service.app import create_app
from audit_log_service.audit_repository import AuditTrailRepository
from audit_log_service.core.config import Settings


@pytest.fixture
def app(mock_client):
    """Create a fresh FastAPI app per test and ensure dependency overrides are cleared."""
    settings = Settings()
    api_app = create_app(settings, injected_client=mock_client)
    try:
        yield api_app
    finally:
        api_app.dependency_overrides.clear()


@pytest.fixture
def mock_client():
    """Mongomock client."""
    return mongomock.MongoClient()


@pytest.fixture
def mongomock_collection(mock_client):
    """
    Provide an isolated in-memory MongoDB collection per test.

    We create a unique DB name to avoid any cross-test contamination, even if a test
    accidentally reuses a client.
    """
    db = mock_client[f"testdb_{uuid4().hex}"]
    col = db["audit_log"]
    return col


@pytest.fixture
def repo(mongomock_collection):
    """AuditTrail repository using a mocked collection."""
    return AuditTrailRepository(mongomock_collection)


@pytest.fixture
def override_repo(app, repo):
    """OVerride `get_repo` function with a repo using mongomock."""
    app.dependency_overrides[get_repo] = lambda: repo
    try:
        yield repo
    finally:
        app.dependency_overrides.pop(get_repo, None)


@pytest.fixture
def client(app, override_repo):
    """
    TestClient with the repo override active.

    Most tests can just depend on `client`. If a test also needs to inspect what's
    in the DB, add `repo` or `override_repo` to its parameters.
    """
    with TestClient(app) as client:
        yield client
