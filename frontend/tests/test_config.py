"""Test frontend configuration."""

import bonsai_app.app as app_module
from bonsai_app.config import Settings


def test_session_cookie_name_from_environment(monkeypatch):
    """Configure Flask's session cookie name through the environment."""
    monkeypatch.setenv("SESSION_COOKIE_NAME", "bonsai_test_session")
    monkeypatch.setattr(app_module, "settings", Settings())

    app = app_module.create_app()

    assert app.config["SESSION_COOKIE_NAME"] == "bonsai_test_session"
