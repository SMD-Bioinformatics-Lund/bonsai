"""Tests for the cluster view metadata formatting."""

from bonsai_app.blueprints.cluster.views import _fmt_object, gather_metadata


def test_fmt_groups_uses_display_names():
    """Group lookup results should be represented by their human-readable names."""
    groups = [
        {"id": "group-1", "display_name": "First group"},
        {"id": "group-2", "display_name": "Second group"},
    ]

    assert _fmt_object("groups", data=groups) == "First group, Second group"


def test_fmt_groups_supports_legacy_string_values():
    """Previously returned string group values should remain supported."""
    assert _fmt_object("groups", data=["First group", "Second group"]) == (
        "First group, Second group"
    )


def test_gather_metadata_formats_group_objects():
    """Group objects from sample summaries should not break GrapeTree metadata."""
    samples = [
        {
            "sample_id": "sample-1",
            "groups": [{"id": "group-1", "display_name": "First group"}],
        }
    ]
    columns = {
        "columns": [
            {"id": "groups", "label": "Groups", "type": "object"},
        ]
    }

    metadata = gather_metadata(samples, columns)

    assert metadata.metadata["sample-1"]["Groups"] == "First group"


def test_gather_metadata_formats_missing_object_as_placeholder():
    """Optional object columns may be absent from some sample summaries."""
    samples = [
        {
            "sample_id": "sample-1",
            "postalignqc_pct_above_x": {"10": 99.5, "30": 95.0},
        },
        {"sample_id": "sample-2", "postalignqc_pct_above_x": None},
    ]
    columns = {
        "columns": [
            {
                "id": "postalignqc_pct_above_x",
                "label": "Coverage breadth above x",
                "type": "object",
            },
        ]
    }

    metadata = gather_metadata(samples, columns)

    assert metadata.metadata["sample-1"]["Coverage breadth above x"] == (
        "10x: 99.5, 30x: 95.0"
    )
    assert metadata.metadata["sample-2"]["Coverage breadth above x"] == "-"
