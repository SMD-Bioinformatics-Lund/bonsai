"""Tests for preparing sample data for clustering jobs."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from bonsai_api.crud.cluster import (
    get_available_cluster_methods,
    get_ska_index_path_for_samples,
    get_typing_profiles,
)
from bonsai_api.exceptions import EntryNotFound
from bonsai_api.models.enums import TypingMethod


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


@pytest.mark.parametrize("ids", [[], ["a"], ["a", "a"]])
def test_cluster_methods_require_two_distinct_samples(ids):
    db = Mock()
    assert asyncio.run(get_available_cluster_methods(db, ids)) == []
    assert not db.mock_calls


@pytest.mark.parametrize(
    "cg_ids,mlst_ids,ska_ids,signatures,existing_ids,expected",
    [
        ({"a", "b"}, {"a", "b"}, {"a", "b"}, [("a", False, 31), ("b", False, 31)],
         {"a", "b"}, {"cgmlst", "mlst", "ska", "minhash"}),
        ({"a"}, {"a", "b"}, {"a"}, [], {"a", "b"}, {"mlst"}),
        (set(), set(), set(), [], {"a", "b"}, set()),
        (set(), set(), set(), [("a", False, 31)], {"a", "b"}, set()),
        (set(), set(), set(), [("a", False, 31), ("b", True, 31)], {"a", "b"}, set()),
        (set(), set(), set(), [("a", False, 31), ("b", False, 31), ("b", False, 51)],
         {"a", "b"}, set()),
        (set(), set(), set(), [("a", False, 31), ("b", False, 51)], {"a", "b"}, set()),
        (set(), set(), set(), [("a", False, None), ("b", False, None)], {"a", "b"}, set()),
        (set(), set(), set(), [("a", False, 31), ("b", False, 31)], {"a"}, set()),
        (set(), set(), set(), [("a", False, 31), ("b", False, 31)],
         {"a", "b"}, {"minhash"}),
    ],
)
def test_cluster_methods_check_the_entire_basket(
    cg_ids, mlst_ids, ska_ids, signatures, existing_ids, expected
):
    """Partial profiles, missing samples, and unavailable signatures hide methods."""
    collection = Mock()
    collection.aggregate = AsyncMock(side_effect=[
        _async_records([
            {"sample_id": sid, "typing_result": {"locus": 0} if sid in typed_ids else {}}
            for sid in existing_ids
        ])
        for typed_ids in (cg_ids, mlst_ids)
    ])
    collection.find.return_value = SimpleNamespace(to_list=AsyncMock(return_value=[
        {"sample_id": sid, "ska_index": f"/{sid}.skf" if sid in ska_ids else None}
        for sid in existing_ids
    ]))
    collection.count_documents = AsyncMock(return_value=len(existing_ids))
    signature_collection = Mock()
    signature_collection.find.return_value = _async_records([
        {"sample_id": sid, "signature_path": f"/{sid}.sig",
         "exclude_from_analysis": excluded, "kmer_size": ksize}
        for sid, excluded, ksize in signatures
    ])
    client = Mock()
    client.get_database.return_value.get_collection.return_value = signature_collection
    db = SimpleNamespace(sample_collection=collection, client=client)

    methods = asyncio.run(get_available_cluster_methods(db, ["a", "b", "a"]))

    assert {method.value for method in methods} == expected
    assert all(isinstance(method, TypingMethod) for method in methods)
