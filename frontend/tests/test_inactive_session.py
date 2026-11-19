"""Rejected accounts must be able to return to the login page."""

from unittest.mock import Mock

import pytest
from bonsai_libs.api_client.core.exceptions import BadRequestError, ServerError, UnauthorizedError
from flask import session

from bonsai_app.bonsai_api import BonsaiApiClient
from bonsai_app.blueprints.login.views import load_user


@pytest.mark.parametrize("path", ["/groups", "/login", "/logout"])
@pytest.mark.parametrize("error", [
    BadRequestError("Inactive user", status=400),
    UnauthorizedError("Expired token", status=401),
])
def test_rejected_session_is_cleared_and_login_remains_accessible(test_app, monkeypatch, path, error):
    monkeypatch.setattr(BonsaiApiClient, "get_current_user", Mock(side_effect=error))
    browser = test_app.test_client()
    with browser.session_transaction() as saved:
        saved.update(_user_id="test-user", _fresh=True, access_token="test-token")

    response = browser.get(path)

    assert response.status_code == (200 if path == "/login" else 302)
    if path != "/login":
        assert response.location == "/logged-out"
    with browser.session_transaction() as saved:
        assert "_user_id" not in saved
        assert "access_token" not in saved
    assert browser.get("/login").status_code == 200
    assert browser.get("/logout").status_code == 302


def test_upstream_server_error_does_not_discard_the_session(test_app, monkeypatch):
    monkeypatch.setattr(BonsaiApiClient, "get_current_user", Mock(side_effect=ServerError("Unavailable", status=503)))
    with test_app.test_request_context():
        session.update(_user_id="test-user", access_token="test-token")

        with pytest.raises(ServerError):
            load_user("test-user")

        assert session["access_token"] == "test-token"
        assert session["_user_id"] == "test-user"
