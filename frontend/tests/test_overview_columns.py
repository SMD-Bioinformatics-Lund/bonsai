"""The all-samples overview requests and renders a bounded column set."""

import re
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bonsai_app.blueprints.groups import views
from bonsai_app.extensions import login_manager


OVERVIEW_IDS = [
    "sample_id", "sample_name", "lims_id", "assay", "release_life_cycle",
    "sequencing_run", "bracken_scientific_name", "qc_status", "comments",
    "tags", "mlst_sequence_type", "stx", "created_at",
]


def sample_table_html(response):
    return response.get_data(as_text=True).split('<table id="sample-table"', 1)[1].split("</table>", 1)[0]


@pytest.fixture
def overview_client(app, user_obj, monkeypatch):
    column_types = {"qc_status": "object", "comments": "object", "tags": "object",
                    "created_at": "date", "analysis_date": "date",
                    "postalignqc_pct_above_x": "object", "groups": "object",
                    "quast_n50": "number"}
    # A visible extra column must not automatically expand the overview either.
    ids = OVERVIEW_IDS + ["groups", "postalignqc_pct_above_x", "quast_n50", "analysis_date"]
    columns = [
        {"id": key, "label": key, "type": column_types.get(key, "string"),
         "sortable": True, "default_visible": key not in OVERVIEW_IDS}
        for key in reversed(ids)
    ]
    sample = {
        "sample_id": "sample-1", "sample_name": "Example sample", "lims_id": "lab-123",
        "qc_status": {"status": "passed"}, "tags": [], "comments": [],
        "created_at": "2026-10-15T12:34:56", "mlst_sequence_type": 0,
        "groups": [{"id": "group-1", "display_name": "Excluded membership"}],
        "postalignqc_pct_above_x": {"10": "excluded-coverage-value"},
        "quast_n50": 123456789,
    }
    response = SimpleNamespace(data={"data": [sample]})
    api = SimpleNamespace(
        get_valid_summary_columns=Mock(return_value={"columns": columns}),
        request_json=Mock(return_value=response),
        get_sample_summaries=Mock(),
    )
    monkeypatch.setattr(views, "get_api_client", lambda: api)
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda _id: user_obj)
    app.jinja_env.globals["asset_url"] = lambda name: f"/static/{name}"
    with app.test_client(user=user_obj) as client:
        yield client, api, response, sample


def test_overview_requests_only_selected_fields_and_renders_all_of_them(overview_client):
    client, api, _, _ = overview_client
    response = client.get("/groups")
    assert response.status_code == 200
    api.request_json.assert_called_once_with(
        "POST", "samples/summary",
        json={"fields": OVERVIEW_IDS, "sort": "-created_at", "limit": 0, "offset": 0},
        expected_status=(200,),
    )
    api.get_sample_summaries.assert_not_called()
    table = sample_table_html(response)
    assert re.findall(r'data-column-id="([^"]+)"', table) == OVERVIEW_IDS
    assert table.count('data-visible="true"') == 13
    assert table.count("<td") == 13
    assert '<a href="/sample/sample-1">Open</a>' in table
    assert b"Excluded membership" not in response.data
    assert b"excluded-coverage-value" not in response.data
    assert b"123,456,789" not in response.data


def test_overview_keeps_all_samples_and_existing_cell_formatting(overview_client):
    client, _, response, sample = overview_client
    response.data = {"data": [
        {**sample, "sample_id": f"sample-{i}", "sample_name": "<script>unsafe</script>"}
        for i in range(5000)
    ]}
    result = client.get("/groups")
    assert result.status_code == 200
    table = sample_table_html(result)
    rows = re.findall(r'<tr id="([^"]+)"[^>]*>(.*?)</tr>', table, re.DOTALL)
    assert len(rows) == 5000
    assert rows[-1][0] == "sample-4999"
    cells = re.findall(r'<td\b([^>]*)>(.*?)</td>', rows[0][1], re.DOTALL)
    assert len(cells) == 13
    assert cells[10][1].strip() == "0"
    assert 'data-order="2026-10-15T12:34:56"' in cells[12][0]
    assert b"&lt;script&gt;unsafe&lt;/script&gt;" in result.data
    assert b"<script>unsafe</script>" not in result.data


def test_empty_overview_still_renders_headers(overview_client):
    client, _, response, _ = overview_client
    response.data = {"data": []}
    result = client.get("/groups")
    assert result.status_code == 200
    table = sample_table_html(result)
    assert re.findall(r'data-column-id="([^"]+)"', table) == OVERVIEW_IDS
    assert '<tr id=' not in table


def test_overview_requires_login(app):
    assert app.test_client().get("/groups").status_code == 302
