"""Identifier filtering works independently of the rendered table columns."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from bs4 import BeautifulSoup

from bonsai_app.blueprints.groups import views
from bonsai_app.extensions import login_manager


@pytest.mark.parametrize("qc", [False, True])
def test_group_rows_expose_identifiers_when_columns_are_omitted(
    app, user_obj, monkeypatch, qc
):
    columns = [
        {"id": "sample_id", "label": "Id", "type": "string", "sortable": False},
        {"id": "created_at", "label": "Uploaded", "type": "date", "sortable": True},
    ]
    sample = {
        "sample_id": "sample-1",
        "sample_name": 'Sample "A" <tag>',
        "external_sample_id": 'LAB-123" onclick="unsafe',
        "created_at": "2026-11-13T10:00:00",
    }
    group = SimpleNamespace(
        display_name="Example group", description="", table_columns=[],
        modified_at="2026-11-13T10:00:00",
    )
    api = SimpleNamespace(
        get_group=Mock(return_value=group),
        get_sample_summaries=Mock(return_value={"data": [sample]}),
        request_json=Mock(return_value=SimpleNamespace(data={"data": [sample]})),
    )
    monkeypatch.setattr(views, "get_api_client", lambda: api)
    monkeypatch.setattr(views, "_get_group_table_columns", lambda *_: columns)
    monkeypatch.setattr(views, "get_qc_table_columns", lambda *_: columns)
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda _: user_obj)
    app.jinja_env.globals["asset_url"] = lambda name: f"/static/{name}"

    with app.test_client(user=user_obj) as client:
        response = client.get(f"/groups/group-1?qc={'true' if qc else 'false'}")

    assert response.status_code == 200
    dom = BeautifulSoup(response.data, "html.parser")
    row = dom.select_one("#sample-table tbody tr")
    assert row["data-sample-name"] == sample["sample_name"]
    assert row["data-lab-id"] == sample["external_sample_id"]
    assert "onclick" not in row.attrs
    assert row.find("tag") is None
    assert [col["data-column-id"] for col in dom.select("#sample-table th")] == [
        "sample_id", "created_at",
    ]
    assert dom.select_one("#sample-id-filter-feedback")["data-scope"] == "this group"
    assert "within this group" in dom.select_one("#sample-id-filter-help").get_text()
    assert dom.select_one('label[for="sample-id-filter-input"]')
    if qc:
        api.request_json.assert_called_once_with(
            "POST", "samples/summary",
            json={
                "group_id": "group-1",
                "fields": ["sample_id", "created_at", "sample_name", "external_sample_id"],
                "sort": "-created_at", "limit": 0, "offset": 0,
            },
            expected_status=(200,),
        )
    else:
        api.get_sample_summaries.assert_called_once_with(group_id="group-1", limit=None)


def test_identifier_attributes_handle_absent_optional_identifiers(app):
    template = app.jinja_env.from_string(
        '{% from "shared.html" import sample_table %}{{ sample_table(table) }}'
    )
    html = template.render(table={"columns": [], "rows": [
        {"sample_id": "id-1"},
        {"sample_id": "id-2", "sample_name": None, "external_sample_id": None},
    ]})
    dom = BeautifulSoup(html, "html.parser")
    for row in dom.select("#sample-table tbody tr"):
        assert row["data-sample-name"] == ""
        assert row["data-lab-id"] == ""
    assert dom.select_one("#sample-id-filter-feedback")["data-scope"] == "this table"
