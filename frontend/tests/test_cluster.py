"""Tests for the cluster view metadata formatting."""

from bonsai_app.blueprints.cluster.views import gather_metadata


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


def test_gather_metadata_uses_lab_id_without_exposing_internal_id():
    """The UUID remains the join key but is not offered as display metadata."""
    samples = [
        {
            "sample_id": "01991d8e-5d6d-7000-8000-000000000001",
            "external_sample_id": "LAB-123",
        }
    ]
    columns = {
        "columns": [
            {"id": "sample_id", "label": "Id", "type": "string"},
            {"id": "external_sample_id", "label": "Lab ID", "type": "string"},
        ]
    }

    metadata = gather_metadata(samples, columns)

    assert metadata.metadata == {
        "01991d8e-5d6d-7000-8000-000000000001": {"Lab ID": "LAB-123"}
    }
    assert "Id" not in metadata.metadata_list
