"""Tests for login session and logout views."""

from bonsai_libs.api_client.core.exceptions import UnauthorizedError

from bonsai_app.blueprints.login import views as login_views


class ExpiredSessionClient:
    """API client stub that represents an expired session token."""

    def __init__(self, *args, **kwargs):
        pass

    def get_current_user(self):
        raise UnauthorizedError("Session expired", status=401)


def test_logout_displays_confirmation_page(test_app):
    """An explicit logout should end the session and show a friendly page."""
    test_app.config["LOGIN_DISABLED"] = True
    client = test_app.test_client()

    with client.session_transaction() as user_session:
        user_session["access_token"] = "secret-token"

    response = client.get("/logout", follow_redirects=True)

    assert response.status_code == 200
    assert response.request.path == "/logged-out"
    assert b"You have been logged out" in response.data
    assert b"Log in again" in response.data
    with client.session_transaction() as user_session:
        assert "access_token" not in user_session


def test_expired_session_redirects_to_logged_out_page(test_app, monkeypatch):
    """An expired token should not make Flask-Login treat a response as a user."""
    monkeypatch.setattr(login_views, "BonsaiApiClient", ExpiredSessionClient)
    client = test_app.test_client()

    with client.session_transaction() as user_session:
        user_session["_user_id"] = "admin"
        user_session["access_token"] = "expired-token"

    response = client.get("/groups", follow_redirects=True)

    assert response.status_code == 200
    assert response.request.path == "/logged-out"
    assert b"You have been logged out" in response.data


def test_first_time_unauthorized_visitor_still_sees_login(test_client):
    """Visitors without an expired session should go directly to login."""
    response = test_client.get("/groups", follow_redirects=True)

    assert response.status_code == 200
    assert response.request.path == "/login"
    assert b"Welcome! Log in" in response.data
