"""Tests for preparing sample data for clustering jobs."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import mongomock
from bonsai_api.crud.builder.summary import build_summary_entry_stages
from bonsai_api.crud.cluster import (
    CLUSTER_TYPING_SPECS,
    get_ska_index_path_for_samples,
    get_typing_profiles,
)
from bonsai_api.exceptions import EntryNotFound


def test_mlst_query_selects_a_stored_profile_with_st_and_alleles():
    sample = json.loads(
        (Path(__file__).parents[1] / "data" / "test_ecoli_1.json").read_text()
    )
    expected = next(entry for entry in sample["typing_result"] if entry["software"] == "mlst")
    collection = mongomock.MongoClient().db.samples
    collection.insert_one(sample)
    # Exercise the generated selection against the stored schema. Later stages
    # use MongoDB operations unsupported by mongomock.
    selection = build_summary_entry_stages(CLUSTER_TYPING_SPECS["mlst"])[0]
    result = next(collection.aggregate([selection]))["__typing_result_sel_array"]
    assert result["result"]["sequence_type"] == expected["result"]["sequence_type"]
    assert result["result"]["alleles"] == expected["result"]["alleles"]


async def _async_records(records):
    for record in records:
        yield record


@pytest.mark.parametrize(
    ("typing_method", "stored_alleles", "expected_result", "expected_profile"),
    [
        (
            "mlst",
            {
                "adk": 1,
                "fumC": None,
                "gyrB": ["2", "3"],
                "icd": "partial",
                "mdh": "novel",
            },
            {
                "adk": 1,
                "fumC": None,
                "gyrB": ["2", "3"],
                "icd": "partial",
                "mdh": "novel",
            },
            {"adk": 1, "fumC": None, "gyrB": None, "icd": None, "mdh": None},
        ),
        (
            "cgmlst",
            {"a": 1, "b": "2", "c": "INF-3", "d": "*4", "e": "LNF", "f": None},
            {"a": 1, "b": 2, "c": 3, "d": 4, "e": None, "f": None},
            {"a": 1, "b": 2, "c": 3, "d": 4, "e": None, "f": None},
        ),
    ],
)
def test_get_typing_profiles_handles_missing_and_uncertain_alleles(
    typing_method, stored_alleles, expected_result, expected_profile
):
    """Keep MLST calls intact and normalize cgMLST calls without rejecting nulls."""
    collection = Mock()
    collection.aggregate = AsyncMock(
        return_value=_async_records(
            [{"sample_id": "sample-1", "typing_result": stored_alleles}]
        )
    )
    db = SimpleNamespace(sample_collection=collection)

    profiles = asyncio.run(get_typing_profiles(db, ["sample-1"], typing_method))

    assert len(profiles) == 1
    assert profiles[0].sample_id == "sample-1"
    assert profiles[0].typing_result == expected_result
    assert profiles[0].allele_profile() == expected_profile


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
