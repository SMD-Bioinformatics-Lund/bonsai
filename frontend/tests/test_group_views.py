"""Tests for group view column selection."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bonsai_app.blueprints.groups.views import (
    _extract_columns,
    _get_group_table_columns,
)


def test_group_table_uses_configured_columns():
    """A configured group should use the API's list response."""
    columns = [{"id": "sample_id"}]
    client = Mock()
    client.request_json.return_value = SimpleNamespace(data=columns)
    group_info = SimpleNamespace(table_columns=["sample_id"])

    assert _get_group_table_columns(client, group_info, "group-1") == columns
    client.request_json.assert_called_once_with(
        "GET", "groups/group-1/columns", expected_status=(200,)
    )
    client.get_valid_summary_columns.assert_not_called()


def test_group_table_without_configuration_uses_summary_columns():
    """A new group without configured columns should use manifest defaults."""
    columns = [{"id": "sample_id"}]
    client = Mock()
    client.get_valid_summary_columns.return_value = {"columns": columns}
    group_info = SimpleNamespace(table_columns=[])

    assert _get_group_table_columns(client, group_info, "group-1") == columns
    client.get_valid_summary_columns.assert_called_once_with()
    client.get_valid_group_columns.assert_not_called()


@pytest.mark.parametrize(
    "column_info", [{}, [], {"columns": None}, {"columns": []}]
)
def test_invalid_column_response_is_rejected(column_info):
    """Malformed and empty configurations should result in a controlled error."""
    with pytest.raises(ValueError, match="did not contain any valid columns"):
        _extract_columns(column_info)
