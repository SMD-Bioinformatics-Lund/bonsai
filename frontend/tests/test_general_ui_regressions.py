"""General UI regressions; no analysis execution or interpretation is used."""

from types import SimpleNamespace
from unittest.mock import Mock

from bonsai_libs.api_client.bonsai.models import UserResponse
from bonsai_libs.api_client.core.exceptions import NotFoundError
from bonsai_app.blueprints.admin import views as admin
from bonsai_app.blueprints.sample import views as samples
from bonsai_app.blueprints.sample.controllers import kw_metadata_to_table
from bonsai_app.extensions import login_manager
from bonsai_app.blueprints.login.views import LoginUser


def logged_in(app, monkeypatch, user):
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda user_id: user)
    # These tests exercise views and templates. Actual built assets are checked in Selenium.
    app.context_processor(lambda: {"asset_url": lambda name: "/static/test.js"})
    return app.test_client(user=user)


def test_new_user_accepts_sdk_not_found_and_is_created_once(app, user_obj, monkeypatch):
    api = SimpleNamespace(get_user=Mock(side_effect=NotFoundError("Unused", status=404)), create_user=Mock())
    monkeypatch.setattr(admin, "get_api_client", lambda: api)
    with logged_in(app, monkeypatch, user_obj) as client:
        response = client.post("/admin/users/new", data={"username": "new_user", "first_name": "Test",
            "last_name": "Account", "email": "user@example.org", "password": "TestPassword123",
            "confirm": "TestPassword123", "roles": ["user"]})
    assert response.status_code == 302
    api.create_user.assert_called_once()
    assert api.create_user.call_args.args[0].username == "new_user"


def test_edit_form_accepts_typed_sdk_user_response(app, user_obj, monkeypatch):
    user_obj.authentication_method = "simple"
    user = UserResponse(username="existing_user", first_name="Test", last_name="Account",
                        email="user@example.org", roles=["user"], authentication_method="simple")
    monkeypatch.setattr(admin, "get_api_client", lambda: SimpleNamespace(get_user=lambda _: user))
    with logged_in(app, monkeypatch, user_obj) as client:
        response = client.get("/admin/users/existing_user")
    assert response.status_code == 200
    assert b'value="Test"' in response.data
    assert b'value="user@example.org"' in response.data


def test_nonadmin_routes_redirect_without_querying_admin_api(app, monkeypatch):
    user = LoginUser({"username": "ordinary", "roles": ["user"]}, token="test")
    with logged_in(app, monkeypatch, user) as client:
        for path in ("/admin", "/admin/users", "/admin/users/new", "/admin/users/existing"):
            response = client.get(path)
            assert response.status_code == 302
            assert response.location == "/"


def test_noncontiguous_metadata_categories_keep_every_entry():
    result = kw_metadata_to_table([
        {"fieldname": "First", "category": "A", "value": "One"},
        {"fieldname": "Other", "category": "B", "value": "Two"},
        {"fieldname": "Last", "category": "A", "value": "Three"},
    ])
    assert result["A"]["index"] == ["First", "Last"]
    assert result["A"]["data"] == [["One"], ["Three"]]


def pending_sample():
    return {"sample_id": "record-1", "sample_name": "Pending record", "external_sample_id": "pending",
            "pipeline": None, "sequencing": None, "created_at": "2026-11-07T00:00:00Z",
            "modified_at": "2026-11-07T00:00:00Z", "qc_status": {"status": "unprocessed"},
            "tags": [], "comments": [], "metadata": [], "species_prediction": [], "typing_result": [],
            "element_type_result": [], "qc_result": []}


def test_pending_sample_summary_renders_without_pipeline(app, user_obj, monkeypatch):
    monkeypatch.setattr(samples, "get_api_client", lambda: SimpleNamespace(get_sample_by_id=lambda **_: pending_sample()))
    with logged_in(app, monkeypatch, user_obj) as client:
        response = client.get("/sample/record-1")
    assert response.status_code == 200
    assert b"Pending record" in response.data
    assert b"No completed pipeline" in response.data


def test_metadata_table_is_rendered_in_its_category(app, user_obj, monkeypatch):
    sample = pending_sample()
    sample["metadata"] = [{"fieldname": "Inventory", "category": "general", "type": "table",
        "columns": ["Item", "Count"], "data": [["Desk", 2]], "index": []}]
    monkeypatch.setattr(samples, "get_api_client", lambda: SimpleNamespace(get_sample_by_id=lambda **_: sample))
    with logged_in(app, monkeypatch, user_obj) as client:
        response = client.get("/sample/record-1/metadata")
    assert response.status_code == 200
    assert b"Inventory" in response.data
    assert b"Desk" in response.data
    assert b"Count" in response.data
