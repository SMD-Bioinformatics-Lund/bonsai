"""The overview reuses Jinja cells without embedding all rows in the page."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from bonsai_libs.api_client.core.exceptions import ApiError

from bonsai_app.blueprints.groups import views
from bonsai_app.extensions import login_manager


@pytest.fixture
def overview_client(app, user_obj, monkeypatch):
    columns = [
        {"id": key, "label": key, "type": kind, "sortable": True,
         "default_visible": key != "measurement"}
        for key, kind in [
            ("sample_id", "string"), ("sample_name", "string"),
            ("created_at", "date"), ("measurement", "number"),
            ("tags", "object"), ("qc_status", "object"),
        ]
    ]
    api = SimpleNamespace(
        get_valid_summary_columns=Mock(return_value={"columns": columns}),
        get_sample_summaries=Mock(return_value={"data": [], "records_total": 0}),
    )
    monkeypatch.setattr(views, "get_api_client", lambda: api)
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda _id: user_obj)
    app.jinja_env.globals["asset_url"] = lambda name: f"/static/{name}"
    with app.test_client(user=user_obj) as client:
        yield client, api


def test_overview_page_only_contains_table_shell(overview_client):
    client, api = overview_client
    response = client.get("/groups")
    assert response.status_code == 200
    api.get_sample_summaries.assert_not_called()
    assert b'data-source="/groups/samples-data"' in response.data
    assert b'<tr id=' not in response.data


def test_overview_cells_match_existing_jinja_and_preserve_metadata(overview_client, app):
    client, api = overview_client
    sample = {
        "sample_id": "sample-1", "sample_name": '<img src=x onerror="alert(1)">',
        "created_at": "2026-10-15T12:34:56", "measurement": 1234567,
        "tags": [{"label": '<Flag>"', "severity": "warning", "description": "a > b"}],
        "qc_status": {"status": "failed", "action": "resequence", "comment": "<check>"},
    }
    api.get_sample_summaries.return_value = {"data": [sample]}
    response = client.get("/groups/samples-data")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    data = response.get_json()
    table = views.format_tablular_data([sample], api.get_valid_summary_columns()["columns"])
    with app.test_request_context():
        renderers = app.jinja_env.get_template("cell_fmt.html").make_module()
        for column, cell in zip(table.columns, data["rows"][0]["cells"]):
            original = str(getattr(renderers, column.renderer)(sample[column.id])).strip()
            assert cell["display"] == original.partition(">")[2].rpartition("</td>")[0]
    cells = data["rows"][0]["cells"]
    assert data["rows"][0]["sample_id"] == "sample-1"
    assert '<a href="/sample/sample-1">Open</a>' in cells[0]["display"]
    assert "&lt;img" in cells[1]["display"] and "<img" not in cells[1]["display"]
    assert cells[2]["sort"] == sample["created_at"]
    assert "1,234,567" in cells[3]["display"]
    assert cells[4]["filter"] == '<Flag>" '
    assert "&lt;check&gt;" in cells[5]["display"]
    assert not data["columns"][3]["visible"]
    assert data["columns"][3]["filterable"]
    api.get_sample_summaries.assert_called_once_with(limit=0, offset=0)


def test_overview_keeps_all_five_thousand_samples_and_missing_values(overview_client):
    client, api = overview_client
    api.get_sample_summaries.return_value = {"data": [
        {"sample_id": f"sample-{i}", "measurement": 0 if i == 0 else None,
         "tags": [], "qc_status": {"status": "unprocessed"}}
        for i in range(5000)
    ]}
    page = client.get("/groups")
    data = client.get("/groups/samples-data").get_json()
    assert len(page.data) < 100_000
    assert len(data["rows"]) == 5000
    assert data["rows"][-1]["sample_id"] == "sample-4999"
    assert data["rows"][0]["cells"][3]["display"] == "0"
    assert data["rows"][1]["cells"][2]["sort"] == ""


def test_overview_sample_links_keep_deployment_prefix(overview_client):
    client, api = overview_client
    api.get_sample_summaries.return_value = {"data": [
        {"sample_id": "a/b", "tags": [], "qc_status": {"status": "unprocessed"}}
    ]}
    response = client.get("/groups/samples-data", environ_overrides={"SCRIPT_NAME": "/bonsai"})
    assert '/bonsai/sample/a/b' in response.get_json()["rows"][0]["cells"][0]["display"]


def test_overview_data_requires_login(app):
    assert app.test_client().get("/groups/samples-data").status_code == 302


def test_overview_upstream_failure_is_not_an_empty_success(overview_client):
    client, api = overview_client
    api.get_sample_summaries.side_effect = ApiError("unavailable", status=503)
    assert client.get("/groups/samples-data").status_code == 503
