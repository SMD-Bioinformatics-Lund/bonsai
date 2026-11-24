"""Column relevance is based on sample values rather than rendered placeholders."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bonsai_app.blueprints.groups.controller import format_tablular_data
from bonsai_app.blueprints.groups.views import _get_group_table_columns
from bonsai_app.summary_columns import has_value


@pytest.mark.parametrize("value", [None, "", "  ", "-", "-:-", [], {}, {"x": None}, [""]])
def test_empty_values_are_not_relevant(value):
    assert not has_value(value)


@pytest.mark.parametrize("value", [0, False, "unknown", [0], {"x": False}])
def test_falsy_measurements_are_relevant(value):
    assert has_value(value)


def test_group_filters_keep_populated_columns_without_changing_layout():
    columns = [
        {
            "id": column_id, "label": column_id, "type": "number",
            "sortable": True, "default_visible": False,
        }
        for column_id in ("sample_id", "absent", "zero", "partial", "disabled")
    ]
    columns[-1]["filterable"] = False
    table = format_tablular_data(
        [
            {"sample_id": "a", "zero": 0, "partial": None, "disabled": 5},
            {"sample_id": "b", "partial": 3},
        ],
        columns,
    )
    assert [col.id for col in table.columns if col.filterable] == ["zero", "partial"]
    assert [col.id for col in table.columns] == [col["id"] for col in columns]
    assert all(not col.visible for col in table.columns)


@pytest.mark.parametrize("visible", [True, False])
def test_group_column_uses_effective_visibility(visible):
    table = format_tablular_data(
        [{"sample_id": "sample-1", "quast_n50": 1000}],
        [{
            "id": "quast_n50", "label": "N50", "type": "number", "sortable": True,
            "default_visible": not visible, "visible": visible,
        }],
    )
    assert table.columns[0].visible is visible


def test_group_table_requests_hidden_allowed_columns():
    column = {"id": "quast_n50", "default_visible": False, "visible": False}
    api = Mock()
    api.get_valid_group_columns.return_value = [
        SimpleNamespace(model_dump=lambda **_: column),
    ]

    columns = _get_group_table_columns(api, SimpleNamespace(table_columns=["quast_n50"]), "group-1")

    api.get_valid_group_columns.assert_called_once_with(group_id="group-1", include_invisible=True)
    assert columns == [column]
