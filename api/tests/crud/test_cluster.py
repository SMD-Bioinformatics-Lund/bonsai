"""Tests for preparing sample data for clustering jobs."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import mongomock
from bonsai_api.crud.allele_scheme import validate_typing_schemes
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
        match="(?s)No cgMLST typing profile is available.*LAB-123",
    ):
        asyncio.run(
            get_typing_profiles(
                db,
                ["01991d8e-5d6d-7000-8000-000000000001"],
                "cgmlst",
            )
        )


@pytest.mark.parametrize("ambiguous_call", [None, ["1", "10"]])
def test_mlst_missing_and_multiple_calls_preserve_loci_for_clustering(ambiguous_call):
    """The reported sagalactiae profile keeps four calls and three missing loci."""
    alleles = {
        "adhP": ambiguous_call,
        "sdhA": "partial",
        "glnA": 1,
        "atr": 2,
        "glcK": 2,
        "pheS": 1,
        "tkt": "partial",
    }
    reference = {**alleles, "adhP": 1, "sdhA": 182, "tkt": 153}
    rows = [
        {
            "sample_id": sid,
            "scheme": "sagalactiae",
            "typing_result": calls,
            "typing_pipeline_run_id": "run",
            "pipeline_runs": [{"pipeline_run_id": "run", "assay": "streptococcus"}],
        }
        for sid, calls in [("INS100135", alleles), ("reference", reference)]
    ]
    db = SimpleNamespace(
        sample_collection=SimpleNamespace(
            aggregate=AsyncMock(return_value=_async_records(rows))
        )
    )
    profiles = asyncio.run(
        get_typing_profiles(db, [row["sample_id"] for row in rows], "mlst")
    )
    assert profiles[0].scheme == "sagalactiae"
    assert profiles[0].allele_profile() == {
        "adhP": None,
        "sdhA": None,
        "glnA": 1,
        "atr": 2,
        "glcK": 2,
        "pheS": 1,
        "tkt": None,
    }
    assert set(profiles[0].typing_result) == set(alleles)
    assert validate_typing_schemes(profiles, "mlst").can_cluster


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
