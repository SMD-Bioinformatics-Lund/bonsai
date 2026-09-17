"""Determine which summary fields contain data before display formatting."""

from typing import Any


def has_value(value: Any) -> bool:
    """Empty containers and placeholders are missing; zero and false are values."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in ("", "-")
    if isinstance(value, dict):
        return any(has_value(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(has_value(item) for item in value)
    return True


def has_column_value(sample: dict[str, Any], column_id: str) -> bool:
    """Check the content displayed by a summary column."""
    value = sample.get(column_id)
    if column_id == "comments":
        return any(
            comment.get("displayed") and has_value(comment.get("comment"))
            for comment in value or []
        )
    if column_id == "tags":
        return any(has_value(tag.get("label")) for tag in value or [])
    return has_value(value)


def relevant_column_ids(
    samples: list[dict[str, Any]], columns: list[dict[str, Any]]
) -> set[str]:
    """Keep fields populated in any sample in the complete target collection."""
    return {
        column["id"]
        for column in columns
        if any(has_column_value(sample, column["id"]) for sample in samples)
    }
