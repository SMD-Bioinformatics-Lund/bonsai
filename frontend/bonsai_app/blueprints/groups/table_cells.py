"""Reuse the existing Jinja cells for a deferred DataTables overview."""

from html.parser import HTMLParser

from flask import current_app

from bonsai_app.models import TableData


class _CellHeader(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag != "td":
            raise ValueError("Expected a Jinja table cell")
        self.attrs = dict(attrs)


def render_overview_rows(table: TableData) -> list[dict]:
    """Keep cell contents and DataTables' existing HTML sort/search overrides.

    Only the outer td is removed. The browser creates it when the row is shown,
    so badges, links, escaping and tooltips still come from cell_fmt.html.
    """
    renderers = current_app.jinja_env.get_template("cell_fmt.html").make_module()
    columns = [
        (column.id, getattr(renderers, column.renderer, renderers.text_renderer))
        for column in table.columns
    ]
    rows = []
    for row in table.rows:
        cells = []
        for column_id, renderer in columns:
            value = row.get(column_id, current_app.jinja_env.undefined(name=column_id))
            rendered = str(renderer(value)).strip()
            opening, _, remainder = rendered.partition(">")
            contents, closing, trailing = remainder.rpartition("</td>")
            if not closing or trailing:
                raise ValueError("Expected a complete Jinja table cell")
            # Jinja escapes attribute values, so a literal > ends the opening tag.
            header = _CellHeader()
            header.feed(opening + ">")
            cell = {"display": contents}
            if "data-order" in header.attrs:
                cell["sort"] = header.attrs["data-order"]
            if "data-search" in header.attrs:
                cell["filter"] = header.attrs["data-search"]
            cells.append(cell)
        rows.append({"sample_id": row["sample_id"], "cells": cells})
    return rows
