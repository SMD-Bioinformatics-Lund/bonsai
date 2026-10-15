"""The overview ships data without building every sample's HTML cells."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from bonsai_libs.api_client.core.exceptions import ApiError

from bonsai_app.blueprints.groups import views
from bonsai_app.extensions import login_manager


@pytest.fixture
def overview_client(app, user_obj, monkeypatch):
    columns = [
        {"id": key, "label": key, "type": kind, "sortable": True, "default_visible": True}
        for key, kind in [
            ("sample_id", "string"), ("sample_name", "string"),
            ("created_at", "date"), ("measurement", "number"),
        ]
    ]
    api = SimpleNamespace(
        get_valid_summary_columns=Mock(return_value={"columns": columns}),
        get_sample_summaries=Mock(return_value={"data": [], "records_total": 0}),
    )
    monkeypatch.setattr(views, "get_api_client", lambda: api)
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda _id: user_obj)
    # Built assets need not be present when exercising the template.
    app.jinja_env.globals["asset_url"] = lambda name: f"/static/{name}"
    with app.test_client(user=user_obj) as client:
        yield client, api


def test_overview_html_does_not_fetch_or_embed_samples(overview_client):
    client, api = overview_client
    response = client.get("/groups")
    assert response.status_code == 200
    api.get_sample_summaries.assert_not_called()
    assert b'data-source="/groups/samples-data"' in response.data
    assert b'data-sample-url="/sample/__sample_id__"' in response.data
    assert b'data-default-sort="created_at"' in response.data
    assert b'<tr id=' not in response.data


def test_overview_data_keeps_all_rows_and_falsy_values(overview_client):
    client, api = overview_client
    api.get_sample_summaries.return_value = {
        "data": [
            {"sample_id": "a", "sample_name": "<script>alert(1)</script>", "measurement": 0, "extra": "unused"},
            {"sample_id": "b", "measurement": None},
            {"sample_id": "c", "measurement": False},
        ],
        "records_total": 3,
    }
    response = client.get("/groups/samples-data")
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.headers["Cache-Control"] == "no-store"
    payload = response.get_json()
    assert payload["rows"] == [
        {"sample_id": "a", "sample_name": "<script>alert(1)</script>", "measurement": 0},
        {"sample_id": "b"},
        {"sample_id": "c", "measurement": False},
    ]
    columns = {col["id"]: col for col in payload["columns"]}
    assert columns["measurement"]["filterable"]
    assert not columns["created_at"]["filterable"]
    api.get_sample_summaries.assert_called_once_with(limit=0, offset=0)


def test_five_thousand_samples_stay_compact(overview_client):
    client, api = overview_client
    api.get_sample_summaries.return_value = {
        "data": [
            {"sample_id": f"sample-{i}", "sample_name": f"Isolate {i}",
             "created_at": "2026-10-15T12:00:00", "measurement": None}
            for i in range(5000)
        ],
        "records_total": 5000,
    }
    page = client.get("/groups")
    data = client.get("/groups/samples-data")
    assert len(page.data) < 100_000
    assert len(data.get_json()["rows"]) == 5000
    assert len(data.data) < 600_000


def test_overview_supplies_renderer_names_used_by_jinja(overview_client):
    client, api = overview_client
    api.get_valid_summary_columns.return_value["columns"].extend(
        {"id": key, "label": key, "type": "object", "sortable": True}
        for key in ("qc_status", "groups", "tags", "comments")
    )
    columns = client.get("/groups/samples-data").get_json()["columns"]
    assert {column["id"]: column["renderer"] for column in columns} == {
        "sample_id": "sample_btn_renderer",
        "sample_name": "text_renderer",
        "created_at": "date_renderer",
        "measurement": "number_renderer",
        "qc_status": "qc_status_renderer",
        "groups": "groups_renderer",
        "tags": "tags_renderer",
        "comments": "comments_renderer",
    }


def test_overview_data_requires_login(app):
    assert app.test_client().get("/groups/samples-data").status_code == 302


def test_overview_upstream_failure_is_not_an_empty_success(overview_client):
    client, api = overview_client
    api.get_sample_summaries.side_effect = ApiError("unavailable", status=503)
    assert client.get("/groups/samples-data").status_code == 503
