"""Functions used by view functions to format data."""

import logging
from typing import Any

from bonsai_app.models import TableCell, TableColumn, TableData
from jsonpath2.path import Path as jsonPath

LOG = logging.getLogger(__name__)

SampleInfo = dict[str, Any]


DEFAULT_RENDERERS = {
    "string": "text_renderer",
    "number": "number_renderer",
    "date": "date_renderer",
    "boolean": "boolean_renderer",
    "list": "list_renderer",
}


def _get_renderer(column: dict[str, Any]) -> str:
    """Get the renderer for a given column type."""
    if column["renderer"]:
        return column["renderer"]
    column_type = column["type"]
    if column_type == "custom":
        # Custom renderers are expected to be defined elsewhere
        return column["renderer"] if column["renderer"] else "text_renderer"
    if column_type not in DEFAULT_RENDERERS:
        LOG.warning(
            "No default renderer for column type '%s'. Using 'text_renderer'.",
            column_type,
        )
        return "text_renderer"
    return DEFAULT_RENDERERS[column_type]


def _get_data(sample_info: dict[str, Any], path: str) -> str:
    jpath = jsonPath.parse_str(path)
    data: list[str] = [m.current_value for m in jpath.match(sample_info)]
    return data[0] if len(data) > 0 else ""


def format_tablular_data(
    data: list[dict[str, Any]], column_defs: list[dict[str, Any]]
) -> TableData:
    """Format data for display in a table."""
    rows: list[dict[str, Any]] = []
    for sample_info in data:
        row: TableCell = {
            col["id"]: _get_data(sample_info, col["path"]) for col in column_defs
        }
        if row:
            rows.append(row)
    table_data = TableData(
        columns=[
            TableColumn(
                id=col["id"],
                label=col["label"],
                type=col["type"],
                renderer=_get_renderer(col),
                sortable=col["sortable"],
                searchable=col["searchable"],
                visible=col["visible"],
            )
            for col in column_defs
        ],
        rows=rows,
    )
    return table_data
