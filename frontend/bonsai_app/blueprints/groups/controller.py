"""Functions used by view functions to format data."""

import logging
from typing import Any

from bonsai_app.models import TableCell, TableColumn, TableData
from jsonpath2.path import Path as jsonPath

LOG = logging.getLogger(__name__)

SampleInfo = dict[str, Any]


DEFAULT_RENDERERS = {
    "string": "text_renderer",
    "integer": "number_renderer",
    "number": "number_renderer",
    "date": "date_renderer",
    "boolean": "boolean_renderer",
    "list": "list_renderer",
}


def _get_renderer(column: dict[str, Any]) -> str:
    """Get the renderer for a given column type."""
    col_type = column["type"]
    if renderer := DEFAULT_RENDERERS.get(col_type):
        return renderer

    if col_type == "object":
        return f"{column['id']}_renderer"

    # Fallback
    LOG.warning(
        "No default renderer for column type '%s'. Using 'text_renderer'.",
        col_type,
    )
    return "text_renderer"


def _get_data(sample_info: dict[str, Any], path: str) -> str:
    jpath = jsonPath.parse_str(path)
    data: list[str] = [m.current_value for m in jpath.match(sample_info)]
    return data[0] if len(data) > 0 else ""


def build_updated_presets(column_info: dict[str, Any]) -> dict[str, Any]:
    """Build a new preset from information recieved from the update request."""
    overrides = []
    for position_idx, col in enumerate(column_info.get("table_columns", []), start=1):
        overrides.append(
            {
                "id": col["id"],
                "visible": col["visible"],
                "sortable": col["sortable"],
                "searchable": col["searchable"],
                "order": position_idx,
            }
        )
    preset = {"preset_id": "default", "label": "default", "overrides": overrides}
    return preset


def format_tablular_data(
    data: list[dict[str, Any]], column_defs: list[dict[str, Any]]
) -> TableData:
    """Format data for display in a table."""
    cols = [
        TableColumn(
            id=col["id"],
            label=col["label"],
            type=col["type"],
            renderer=_get_renderer(col),
            sortable=col["sortable"],
            searchable=col["type"] != "object",
            visible=col.get("default_visible", True),
        )
        for col in column_defs
    ]
    table_data = TableData(columns=cols, rows=data)
    return table_data
