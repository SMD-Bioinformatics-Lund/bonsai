"""Admin forms use the SDK's typed user responses and not-found errors."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from bs4 import BeautifulSoup
from bonsai_libs.api_client.bonsai.models import UserResponse
from bonsai_libs.api_client.core.exceptions import NotFoundError

from bonsai_app.blueprints.admin import views
from bonsai_app.extensions import login_manager


@pytest.fixture
def admin_client(app, user_obj, monkeypatch):
    app.config["TESTING"] = True
    user_obj.authentication_method = "simple"
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda _: user_obj)
    with app.test_client(user=user_obj) as client:
        yield client


@pytest.fixture
def user_data():
    return {
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "email": "testuser@example.com",
        "roles": ["user", "uploader"],
        "password": "TestPassword123",
        "confirm": "TestPassword123",
    }


@pytest.fixture
def api(user_data, monkeypatch):
    user = UserResponse(**user_data, authentication_method="simple")
    client = SimpleNamespace(
        get_user=Mock(return_value=user),
        create_user=Mock(return_value=user),
        update_user=Mock(return_value=user),
    )
    monkeypatch.setattr(views, "get_api_client", lambda: client)
    return client


def test_create_new_user_when_username_lookup_returns_not_found(admin_client, api, user_data):
    api.get_user.side_effect = NotFoundError("No such user")

    response = admin_client.post("/admin/users/new", data=user_data)

    assert response.status_code == 302
    assert response.location.endswith("/admin/users")
    api.create_user.assert_called_once()
    created = api.create_user.call_args.args[0]
    assert created.username == user_data["username"]
    assert created.roles == user_data["roles"]


def test_existing_username_is_rejected_without_creating_user(admin_client, api, user_data):
    response = admin_client.post("/admin/users/new", data=user_data)

    assert response.status_code == 200
    assert b"already exists" in response.data
    api.create_user.assert_not_called()


def test_edit_form_is_populated_from_sdk_user_model(admin_client, api, user_data):
    response = admin_client.get("/admin/users/testuser")

    assert response.status_code == 200
    form = BeautifulSoup(response.data, "html.parser")
    for field in ("username", "first_name", "last_name", "email"):
        assert form.find("input", {"name": field})["value"] == user_data[field]
    checked_roles = form.select('input[name="roles"][checked]')
    assert {field["value"] for field in checked_roles} == set(user_data["roles"])
    assert not form.find("input", {"name": "password"}).get("value")


def test_save_user_with_blank_password_reports_success(admin_client, api, user_data):
    response = admin_client.post(
        "/admin/users/testuser",
        data={**user_data, "password": "", "confirm": "", "update": ""},
    )

    assert response.status_code == 200
    assert b"Updated user testuser" in response.data
    api.update_user.assert_called_once()
    assert api.update_user.call_args.kwargs["user_data"]["password"] == ""
