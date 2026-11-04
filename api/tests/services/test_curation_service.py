"""Tests for curation service synchronization."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from bonsai_api.services import curation_service


@pytest.mark.asyncio
async def test_sync_clears_included_analysis_type_when_only_other_type_remains(
    monkeypatch,
):
    """A deleted type is cleared while another type remains curated."""
    monkeypatch.setattr(
        curation_service,
        "get_curations_crud",
        AsyncMock(
            return_value=[
                {
                    "sample_id": "sample-1",
                    "analysis_id": "analysis-1",
                    "analysis_type": "cgmlst",
                    "decision": "accept",
                }
            ]
        ),
    )
    monkeypatch.setattr(
        curation_service,
        "UpdateOne",
        lambda filter_, update: (filter_, update),
    )

    bulk_write = AsyncMock(
        return_value=SimpleNamespace(matched_count=1, acknowledged=True)
    )
    db = SimpleNamespace(sample_collection=SimpleNamespace(bulk_write=bulk_write))

    result = await curation_service.sync_curation_summary_for_analysis(
        db,
        sample_id="sample-1",
        analysis_id="analysis-1",
        include_analysis_types={"amr"},
    )

    operations = bulk_write.await_args.args[0]
    assert (
        {
            "sample_id": "sample-1",
            "element_type_result": {
                "$elemMatch": {
                    "analysis_id": "analysis-1",
                    "analysis_type": "amr",
                }
            },
        },
        {"$set": {"element_type_result.$.curations": []}},
    ) in operations
    assert result is True
