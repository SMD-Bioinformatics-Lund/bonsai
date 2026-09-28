"""Determine which summary fields contain data before display formatting."""

from typing import Any


def has_value(value: Any) -> bool:
    """Empty containers and placeholders are missing; zero and false are values."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in ("", "-")
    if isinstance(value, dict):
        # Comment records are only rendered when explicitly displayed. Tag
        # records are represented by their label; other objects use any
        # meaningful member as their populated value.
        if "displayed" in value and "comment" in value:
            return bool(value["displayed"]) and has_value(value["comment"])
        if "label" in value:
            return has_value(value["label"])
        return any(has_value(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(has_value(item) for item in value)
    return True


def has_column_value(sample: dict[str, Any], column_id: str) -> bool:
    """Check the content displayed by a summary column."""
    return has_value(sample.get(column_id))


def relevant_column_ids(
    samples: list[dict[str, Any]], columns: list[dict[str, Any]]
) -> set[str]:
    """Keep fields populated in any sample in the complete target collection."""
    return {
        column["id"]
        for column in columns
        if any(has_column_value(sample, column["id"]) for sample in samples)
    }
