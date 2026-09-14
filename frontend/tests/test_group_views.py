"""Tests for group table column selection and API failures."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from bonsai_libs.api_client.core.exceptions import ApiRequestFailed, NotFoundError
from werkzeug.exceptions import BadGateway, NotFound

from bonsai_app.blueprints.groups.views import (
    _api_error_status,
    _extract_columns,
    _get_group_table_columns,
    group,
)


COLUMN = {
    "id": "sample_id",
    "label": "Sample ID",
    "type": "string",
    "sortable": True,
}


def test_group_table_uses_configured_columns():
    """A configured group should use the API's bare-list response."""
    client = Mock()
    client.request_json.return_value = SimpleNamespace(data=[COLUMN])
    group_info = SimpleNamespace(table_columns=["sample_id"])

    assert _get_group_table_columns(client, group_info, "group-1") == [COLUMN]
    client.request_json.assert_called_once_with(
        "GET", "groups/group-1/columns", expected_status=(200,)
    )
    client.get_valid_summary_columns.assert_not_called()


def test_group_table_without_configuration_uses_summary_columns():
    """A group without configured columns should use manifest defaults."""
    client = Mock()
    client.get_valid_summary_columns.return_value = {"columns": [COLUMN]}
    group_info = SimpleNamespace(table_columns=[])

    assert _get_group_table_columns(client, group_info, "group-1") == [COLUMN]
    client.get_valid_summary_columns.assert_called_once_with()
    client.request_json.assert_not_called()


def test_extract_columns_accepts_sdk_style_response():
    """SDK-style response objects remain supported during the transition."""
    assert _extract_columns(SimpleNamespace(columns=[COLUMN])) == [COLUMN]


@pytest.mark.parametrize(
    "column_info",
    [
        {},
        [],
        {"columns": None},
        {"columns": []},
        {"columns": ["sample_id"]},
        {"columns": [{"id": "sample_id"}]},
    ],
)
def test_invalid_column_response_is_rejected(column_info):
    """Malformed and incomplete column configurations are rejected."""
    with pytest.raises(ValueError, match="Column configuration"):
        _extract_columns(column_info)


def test_api_error_status_preserves_http_status():
    error = NotFoundError("missing", status=404)
    assert _api_error_status(error) == 404


def test_api_error_status_uses_bad_gateway_without_status():
    assert _api_error_status(ApiRequestFailed("network failure")) == 502


def test_group_view_preserves_group_not_found(test_app):
    """A missing upstream group produces a controlled 404 response."""
    client = Mock()
    client.get_sample_summaries.return_value = {"data": []}
    client.get_group.side_effect = NotFoundError("missing", status=404)

    with test_app.test_request_context("/groups/group-1"):
        with patch(
            "bonsai_app.blueprints.groups.views.get_api_client", return_value=client
        ):
            with pytest.raises(NotFound):
                group.__wrapped__("group-1")


def test_group_view_renders_configured_columns(test_app):
    """Configured groups render using the API's bare-list column response."""
    client = Mock()
    client.get_sample_summaries.return_value = {"data": []}
    client.get_group.return_value = SimpleNamespace(
        table_columns=["sample_id"],
        display_name="Group one",
        description="Test group",
        modified_at="2026-09-14T00:00:00Z",
    )
    client.request_json.return_value = SimpleNamespace(data=[COLUMN])

    with test_app.test_request_context("/groups/group-1"):
        with (
            patch(
                "bonsai_app.blueprints.groups.views.get_api_client",
                return_value=client,
            ),
            patch(
                "bonsai_app.blueprints.groups.views.current_user",
                SimpleNamespace(token="token"),
            ),
            patch(
                "bonsai_app.blueprints.groups.views.render_template",
                return_value="rendered",
            ),
        ):
            assert group.__wrapped__("group-1") == "rendered"


def test_group_view_rejects_invalid_column_response(test_app):
    """Malformed upstream columns produce a controlled bad-gateway response."""
    client = Mock()
    client.get_sample_summaries.return_value = {"data": []}
    client.get_group.return_value = SimpleNamespace(table_columns=["sample_id"])
    client.request_json.return_value = SimpleNamespace(data=[])

    with test_app.test_request_context("/groups/group-1"):
        with patch(
            "bonsai_app.blueprints.groups.views.get_api_client", return_value=client
        ):
            with pytest.raises(BadGateway):
                group.__wrapped__("group-1")


def test_group_view_handles_column_network_failure(test_app):
    """A status-less SDK failure becomes a controlled bad-gateway response."""
    client = Mock()
    client.get_sample_summaries.return_value = {"data": []}
    client.get_group.return_value = SimpleNamespace(table_columns=["sample_id"])
    client.request_json.side_effect = ApiRequestFailed("network failure")

    with test_app.test_request_context("/groups/group-1"):
        with patch(
            "bonsai_app.blueprints.groups.views.get_api_client", return_value=client
        ):
            with pytest.raises(BadGateway):
                group.__wrapped__("group-1")
