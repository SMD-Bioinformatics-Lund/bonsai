"""Frontend settings must reach the SDK's HTTP transport, including authentication."""

import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest
import requests
from requests.adapters import BaseAdapter

import bonsai_app.bonsai_api as api_module


class RecordingAdapter(BaseAdapter):
    def __init__(self):
        self.calls = []

    def send(self, request, **kwargs):
        self.calls.append((request, kwargs))
        body = (
            {"access_token": "test-token", "token_type": "bearer"}
            if urlparse(request.url).path == "/token"
            else {
                "username": "test-user", "email": "test@example.org",
                "roles": ["user"], "authentication_method": "simple",
            }
        )
        response = requests.Response()
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        response._content = json.dumps(body).encode()
        response.request = request
        return response

    def close(self):
        pass


@pytest.fixture
def transport(monkeypatch):
    adapter = RecordingAdapter()
    http_session = requests.Session()
    http_session.mount("https://", adapter)
    monkeypatch.setattr(requests, "Session", lambda: http_session)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("CURL_CA_BUNDLE", raising=False)
    return adapter


@pytest.mark.parametrize("verify", [True, False, Path("/tmp/test-ca.pem"), "/tmp/test-ca.pem"])
def test_request_client_passes_timeout_and_tls_settings(test_app, monkeypatch, transport, verify):
    test_app.config.update(API_INTERNAL_URL="https://api.invalid", VERIFY_SSL=verify, REQUEST_TIMEOUT=71)
    monkeypatch.setattr(api_module, "current_user", SimpleNamespace(token="test-token"))
    with test_app.test_request_context():
        api_module.get_api_client().get("users/me")

    request, options = transport.calls[0]
    assert options["timeout"] == 71
    assert options["verify"] == (str(verify) if isinstance(verify, Path) else verify)
    assert request.headers["Authorization"] == "Bearer test-token"


def test_login_and_session_reload_use_configured_transport(test_app, transport):
    test_app.config.update(
        API_INTERNAL_URL="https://api.invalid", VERIFY_SSL=False, REQUEST_TIMEOUT=83,
    )
    browser = test_app.test_client()
    response = browser.post("/login", data={"username": "test-user", "password": "test-password"})
    assert response.status_code == 302
    assert response.location == "/groups"

    assert browser.get("/logged-out").status_code == 200
    assert [urlparse(request.url).path for request, _ in transport.calls] == [
        "/token", "/users/me", "/users/me",
    ]
    assert all(options["timeout"] == 83 and options["verify"] is False for _, options in transport.calls)
    assert "Authorization" not in transport.calls[0][0].headers
    assert all(request.headers["Authorization"] == "Bearer test-token" for request, _ in transport.calls[1:])
