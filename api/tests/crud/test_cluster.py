"""Tests for preparing sample data for clustering jobs."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from bonsai_api.crud.cluster import (
    get_ska_index_path_for_samples,
    get_typing_profiles,
)
from bonsai_api.exceptions import EntryNotFound


async def _async_records(records):
    for record in records:
        yield record


def test_get_typing_profiles_rejects_empty_profile_with_lab_id():
    """An existing sample without a profile is reported using its Lab ID."""
    collection = Mock()
    collection.aggregate = AsyncMock(
        return_value=_async_records(
            [
                {
                    "sample_id": "01991d8e-5d6d-7000-8000-000000000001",
                    "external_sample_id": "LAB-123",
                    "typing_result": {},
                }
            ]
        )
    )
    db = SimpleNamespace(sample_collection=collection)

    with pytest.raises(
        EntryNotFound,
        match="No cgMLST typing profile is available.*LAB-123",
    ):
        asyncio.run(
            get_typing_profiles(
                db,
                ["01991d8e-5d6d-7000-8000-000000000001"],
                "cgmlst",
            )
        )


def test_get_ska_indexes_rejects_missing_index_with_lab_id():
    """A sample without an SKA index is reported using its Lab ID."""
    cursor = SimpleNamespace(
        to_list=AsyncMock(
            return_value=[
                {
                    "sample_id": "01991d8e-5d6d-7000-8000-000000000001",
                    "external_sample_id": "LAB-123",
                    "ska_index": None,
                }
            ]
        )
    )
    collection = Mock()
    collection.find.return_value = cursor
    db = SimpleNamespace(sample_collection=collection)

    with pytest.raises(
        EntryNotFound,
        match="No SKA index is available.*LAB-123",
    ):
        asyncio.run(
            get_ska_index_path_for_samples(
                db,
                ["01991d8e-5d6d-7000-8000-000000000001"],
            )
        )
