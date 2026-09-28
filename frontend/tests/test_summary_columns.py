"""Column relevance is based on sample values rather than rendered placeholders."""

import pytest

from bonsai_app.blueprints.groups.controller import format_tablular_data
from bonsai_app.summary_columns import has_value


@pytest.mark.parametrize("value", [None, "", "  ", "-", [], {}, {"x": None}, [""]])
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
