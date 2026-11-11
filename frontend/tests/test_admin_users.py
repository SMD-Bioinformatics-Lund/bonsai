"""Exercise admin access, rendered user forms, validation, and API operations."""

from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from bs4 import BeautifulSoup
from bonsai_libs.api_client.bonsai.models import UserResponse
from bonsai_libs.api_client.core.exceptions import (
    ConflictError,
    NetworkError,
    NotFoundError,
    ServerError,
)

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
        get_users=Mock(return_value=[user]),
        get_user=Mock(return_value=user),
        create_user=Mock(return_value=user),
        update_user=Mock(return_value=user),
        delete_user=Mock(),
    )
    monkeypatch.setattr(views, "get_api_client", lambda: client)
    return client


ADMIN_ROUTES = [
    ("GET", "/admin"),
    ("GET", "/admin/users"),
    ("GET", "/admin/users/new"),
    ("POST", "/admin/users/new"),
    ("GET", "/admin/users/testuser"),
    ("POST", "/admin/users/testuser"),
    ("POST", "/admin/users/delete"),
]


@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
def test_anonymous_requests_require_login(app, monkeypatch, method, path):
    api_factory = Mock()
    monkeypatch.setattr(views, "get_api_client", api_factory)

    with app.test_client() as client:
        response = client.open(path, method=method)

    assert response.status_code == 302
    assert response.location == "/login"
    api_factory.assert_not_called()


@pytest.mark.parametrize("roles", [[], ["user"], ["uploader"], ["user", "uploader"]])
@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
def test_non_admin_requests_cannot_access_users(
    admin_client, user_obj, monkeypatch, roles, method, path
):
    user_obj.roles = roles
    api_factory = Mock()
    monkeypatch.setattr(views, "get_api_client", api_factory)

    response = admin_client.open(path, method=method)

    assert response.status_code == 302
    assert response.location == "/"
    with admin_client.session_transaction() as session:
        assert (
            "warning", "You don't have permission to view this page"
        ) in session["_flashes"]
    api_factory.assert_not_called()


def test_admin_landing_redirects_to_users(admin_client, api):
    response = admin_client.get("/admin")

    assert response.status_code == 302
    assert response.location == "/admin/users"


@pytest.mark.parametrize("empty", [False, True])
def test_user_list_renders_sdk_users_and_edit_links(admin_client, api, user_data, empty):
    if empty:
        api.get_users.return_value = []

    response = admin_client.get("/admin/users")

    assert response.status_code == 200
    page = BeautifulSoup(response.data, "html.parser")
    rows = page.select("tbody tr")
    assert len(rows) == (0 if empty else 1)
    assert page.find("a", href="/admin/users/new")
    assert page.find("form")["action"] == "/admin/users/delete"
    if not empty:
        edit_link = rows[0].find("a", href="/admin/users/testuser")
        assert edit_link.get_text(strip=True) == "testuser"
        assert rows[0].find("input", {"name": "testuser", "type": "checkbox"})
        assert user_data["email"] in rows[0].get_text()
        assert all(role in rows[0].get_text() for role in user_data["roles"])
    assert user_data["password"].encode() not in response.data
    api.get_users.assert_called_once_with()


def test_create_form_get_does_not_check_username(admin_client, api):
    response = admin_client.get("/admin/users/new")

    assert response.status_code == 200
    page = BeautifulSoup(response.data, "html.parser")
    assert page.find("form")["action"] == "/admin/users/new"
    assert not page.select(".invalid-feedback")
    assert not page.select('input[name="roles"][checked]')
    api.get_user.assert_not_called()
    api.create_user.assert_not_called()


def test_create_new_user_when_username_lookup_returns_not_found(admin_client, api, user_data):
    api.get_user.side_effect = NotFoundError("No such user")

    response = admin_client.post("/admin/users/new", data=user_data)

    assert response.status_code == 302
    assert response.location.endswith("/admin/users")
    api.create_user.assert_called_once()
    created = api.create_user.call_args.args[0]
    assert created.username == user_data["username"]
    assert created.roles == user_data["roles"]
    assert created.first_name == user_data["first_name"]
    assert created.last_name == user_data["last_name"]
    assert created.email == user_data["email"]
    assert created.password == user_data["password"]
    api.get_user.assert_called_once_with(user_data["username"])
    api.update_user.assert_not_called()
    api.delete_user.assert_not_called()


def test_existing_username_is_rejected_without_creating_user(admin_client, api, user_data):
    response = admin_client.post("/admin/users/new", data=user_data)

    assert response.status_code == 200
    assert b"A user with username testuser already exists" in response.data
    api.create_user.assert_not_called()


@pytest.mark.parametrize("username", [None, "", "abc", "a" * 26])
def test_invalid_username_does_not_trigger_lookup(admin_client, api, user_data, username):
    data = {**user_data, "username": username}
    if username is None:
        data.pop("username")

    response = admin_client.post("/admin/users/new", data=data)

    assert response.status_code == 200
    form = BeautifulSoup(response.data, "html.parser")
    username_field = form.find("input", {"name": "username"})
    assert "is-invalid" in username_field.parent["class"]
    assert b"already exists" not in response.data
    api.get_user.assert_not_called()
    api.create_user.assert_not_called()


def test_partial_form_shows_errors_without_creating_user(admin_client, api):
    api.get_user.side_effect = NotFoundError("No such user")

    response = admin_client.post(
        "/admin/users/new", data={"username": "newuser", "first_name": "Test"}
    )

    assert response.status_code == 200
    form = BeautifulSoup(response.data, "html.parser")
    assert form.find("input", {"name": "username"})["value"] == "newuser"
    assert form.find("input", {"name": "first_name"})["value"] == "Test"
    email_field = form.find("input", {"name": "email"})
    assert email_field.parent.find_next_sibling(class_="invalid-feedback")
    api.get_user.assert_called_once_with("newuser")
    api.create_user.assert_not_called()


INVALID_FIELDS = [
    ("username", ""),
    ("username", "abc"),
    ("username", "a" * 26),
    ("first_name", ""),
    ("first_name", "A"),
    ("first_name", "A" * 51),
    ("last_name", ""),
    ("last_name", "A"),
    ("last_name", "A" * 51),
    ("email", ""),
    ("email", "not-an-email"),
    ("password", "Aa12345"),
    ("password", "Aa1" + "x" * 70),
    ("password", "alllowercase123"),
    ("password", "ALLUPPERCASE123"),
    ("password", "NoDigitsHere"),
    ("password", "Password123 "),
    ("confirm", "DifferentPassword123"),
    ("roles", []),
    ("roles", ["unknown"]),
    ("roles", ["user", "unknown"]),
]


@pytest.mark.parametrize("operation", ["create", "update"])
@pytest.mark.parametrize(
    "field,value", INVALID_FIELDS, ids=[name for name, _ in INVALID_FIELDS]
)
def test_invalid_forms_never_mutate_users(
    admin_client, api, user_data, operation, field, value
):
    data = {**user_data, field: value}
    if field == "password":
        data["confirm"] = value
    if operation == "create":
        api.get_user.side_effect = NotFoundError("No such user")
        path = "/admin/users/new"
    else:
        data["update"] = ""
        path = "/admin/users/testuser"

    response = admin_client.post(path, data=data)

    assert response.status_code == 200
    page = BeautifulSoup(response.data, "html.parser")
    # A mismatched confirmation is reported against the password field.
    invalid_field = "password" if field == "confirm" else field
    assert "is-invalid" in page.find(id=invalid_field).parent["class"]
    assert page.select(".invalid-feedback")
    if field == "roles" and not value:
        assert b"At least one role must be selected" in response.data
    if field == "password" and value in (
        "alllowercase123", "ALLUPPERCASE123", "NoDigitsHere"
    ):
        assert (
            b"The password must include uppercase and lowercase letters "
            b"and at least one number."
        ) in response.data
    api.create_user.assert_not_called()
    api.update_user.assert_not_called()
    api.delete_user.assert_not_called()


@pytest.mark.parametrize(
    "missing_field",
    ["username", "first_name", "last_name", "email", "password", "confirm", "roles"],
)
def test_missing_registration_fields_never_create_users(
    admin_client, api, user_data, missing_field
):
    api.get_user.side_effect = NotFoundError("No such user")
    data = {key: value for key, value in user_data.items() if key != missing_field}

    response = admin_client.post("/admin/users/new", data=data)

    assert response.status_code == 200
    api.create_user.assert_not_called()


@pytest.mark.parametrize(
    "roles", [["admin"], ["user"], ["uploader"], ["admin", "user", "uploader"]]
)
@pytest.mark.parametrize("boundary", ["minimum", "maximum"])
def test_valid_registration_boundaries_and_roles(
    admin_client, api, user_data, roles, boundary
):
    api.get_user.side_effect = NotFoundError("No such user")
    password = "Abcdef12" if boundary == "minimum" else "Aa1" + "x" * 69
    data = {
        **user_data,
        "username": "user" if boundary == "minimum" else "u" * 25,
        "first_name": "Al" if boundary == "minimum" else "A" * 50,
        "last_name": "Li" if boundary == "minimum" else "L" * 50,
        "password": password,
        "confirm": password,
        "roles": roles,
    }

    response = admin_client.post("/admin/users/new", data=data)

    assert response.status_code == 302
    api.create_user.assert_called_once()
    created = api.create_user.call_args.args[0]
    assert created.username == data["username"]
    assert created.password == password
    assert created.roles == roles


@pytest.mark.parametrize("error_type", [NetworkError, ServerError])
def test_username_lookup_failures_show_validation_error(
    admin_client, api, user_data, error_type
):
    api.get_user.side_effect = error_type("API unavailable")

    response = admin_client.post("/admin/users/new", data=user_data)

    assert response.status_code == 200
    assert b"Could not check username availability. Please try again." in response.data
    assert b"already exists" not in response.data
    api.create_user.assert_not_called()


@pytest.mark.parametrize("error_type", [ConflictError, NetworkError, ServerError])
def test_creation_failure_does_not_crash_or_report_success(
    admin_client, api, user_data, error_type
):
    api.get_user.side_effect = NotFoundError("No such user")
    api.create_user.side_effect = error_type("Creation failed")

    response = admin_client.post("/admin/users/new", data=user_data)

    assert response.status_code == 200
    assert b"An error occurred when creating the user. Please try again." in response.data
    assert b"Created new user" not in response.data
    page = BeautifulSoup(response.data, "html.parser")
    assert page.find("input", {"name": "username"})["value"] == user_data["username"]
    api.create_user.assert_called_once()


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


def test_save_profile_roles_and_new_password(admin_client, api, user_data):
    data = {
        **user_data,
        "first_name": "Updated",
        "roles": ["admin"],
        "password": "NewPassword123",
        "confirm": "NewPassword123",
        "update": "",
    }

    response = admin_client.post("/admin/users/testuser", data=data)

    assert response.status_code == 200
    assert b"Updated user testuser" in response.data
    api.update_user.assert_called_once()
    assert api.update_user.call_args.kwargs["username"] == "testuser"
    submitted = api.update_user.call_args.kwargs["user_data"]
    assert submitted["first_name"] == "Updated"
    assert submitted["roles"] == ["admin"]
    assert submitted["password"] == "NewPassword123"
    assert b"NewPassword123" not in response.data
    api.delete_user.assert_not_called()


def test_update_failure_shows_warning_without_success(admin_client, api, user_data):
    api.update_user.side_effect = NetworkError("API unavailable")

    response = admin_client.post("/admin/users/testuser", data={**user_data, "update": ""})

    assert response.status_code == 200
    assert b"An error occurred when updating user info" in response.data
    assert b"Updated user testuser" not in response.data
    api.delete_user.assert_not_called()


def test_ldap_edit_disables_both_password_fields(admin_client, user_obj, api):
    user_obj.authentication_method = "ldap"

    response = admin_client.get("/admin/users/testuser")

    assert response.status_code == 200
    page = BeautifulSoup(response.data, "html.parser")
    for name in ("password", "confirm"):
        assert page.find("input", {"name": name}).has_attr("disabled")
    assert b"Passwords are managed by the ldap server" in response.data


@pytest.mark.parametrize("page_path", ["/admin/users", "/admin/users/testuser"])
def test_user_names_are_html_escaped(admin_client, api, page_path):
    unsafe_name = '<script>alert("name")</script>'
    api.get_user.return_value.first_name = unsafe_name

    response = admin_client.get(page_path)

    assert response.status_code == 200
    assert unsafe_name.encode() not in response.data
    page = BeautifulSoup(response.data, "html.parser")
    if page_path == "/admin/users":
        assert unsafe_name in page.select_one("tbody").get_text()
    else:
        assert page.find("input", {"name": "first_name"})["value"] == unsafe_name


@pytest.mark.parametrize("error", [None, NetworkError("API unavailable")])
def test_delete_from_edit_form_reports_result(admin_client, api, user_data, error):
    api.delete_user.side_effect = error

    response = admin_client.post(
        "/admin/users/testuser",
        data={**user_data, "password": "", "confirm": "", "delete": ""},
    )

    assert response.status_code == 200
    api.delete_user.assert_called_once_with("testuser")
    api.update_user.assert_not_called()
    if error:
        assert b"An error occurred when removing testuser" in response.data
        assert b"Removed user testuser" not in response.data
    else:
        assert b"Removed user testuser" in response.data


def test_edit_post_without_action_does_not_delete_user(admin_client, api, user_data):
    response = admin_client.post("/admin/users/testuser", data=user_data)

    assert response.status_code == 200
    api.update_user.assert_not_called()
    api.delete_user.assert_not_called()


@pytest.mark.parametrize("referrer", [None, "/admin/users"])
@pytest.mark.parametrize("selected", [False, True])
def test_bulk_delete_only_selected_users(admin_client, api, referrer, selected):
    headers = {"Referer": referrer} if referrer else {}
    data = (
        {"testuser": "on", "seconduser": "on", "unselected": "off"} if selected else {}
    )

    response = admin_client.post("/admin/users/delete", data=data, headers=headers)

    assert response.status_code == 302
    assert response.location == "/admin/users"
    expected_calls = [call("testuser"), call("seconduser")] if selected else []
    assert api.delete_user.call_args_list == expected_calls
    with admin_client.session_transaction() as session:
        flashes = session.get("_flashes", [])
    expected_flashes = (
        [("success", "Deleted users: testuser, seconduser")] if selected else []
    )
    assert flashes == expected_flashes


def test_bulk_delete_reports_partial_failure_and_continues(admin_client, api):
    api.delete_user.side_effect = [NetworkError("API unavailable"), None]

    response = admin_client.post(
        "/admin/users/delete",
        data={"faileduser": "on", "deleteduser": "on"},
        headers={"Referer": "/admin/users"},
    )

    assert response.status_code == 302
    assert response.location == "/admin/users"
    assert api.delete_user.call_args_list == [call("faileduser"), call("deleteduser")]
    with admin_client.session_transaction() as session:
        assert ("danger", "Error when deleting user: faileduser") in session["_flashes"]
        assert ("success", "Deleted users: deleteduser") in session["_flashes"]
