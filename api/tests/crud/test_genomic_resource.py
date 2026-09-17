"""Tests for genomic-resource persistence operations."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bonsai_api.crud.genomic_resource import (
    insert_genomic_resource,
    sample_has_resource,
)


def test_resource_lookup_is_scoped_to_sample():
    collection = SimpleNamespace(find_one=AsyncMock(return_value={"_id": "sample"}))
    db = SimpleNamespace(sample_collection=collection)

    found = asyncio.run(
        sample_has_resource(db, sample_id="sample-1", pipeline_id="run-1")
    )

    assert found is True
    collection.find_one.assert_awaited_once_with(
        {
            "sample_id": "sample-1",
            "genomic_resources.pipeline_id": "run-1",
        },
        {"_id": 1},
        session=None,
    )


def test_force_replaces_resources_from_matching_pipeline():
    collection = SimpleNamespace(update_one=AsyncMock())
    db = SimpleNamespace(sample_collection=collection)
    resources = [{"id": "new", "pipeline_id": "run-1"}]

    asyncio.run(
        insert_genomic_resource(
            db,
            sample_id="sample-1",
            pipeline_id="run-1",
            resource_data=resources,
            replace=True,
        )
    )

    query, update = collection.update_one.await_args.args
    assert query == {"sample_id": "sample-1"}
    assert update[0]["$set"]["genomic_resources"]["$concatArrays"][1] == resources
    filtered = update[0]["$set"]["genomic_resources"]["$concatArrays"][0]
    assert filtered["$filter"]["cond"] == {
        "$ne": ["$$resource.pipeline_id", "run-1"]
    }


def test_regular_insert_appends_resources():
    collection = SimpleNamespace(update_one=AsyncMock())
    db = SimpleNamespace(sample_collection=collection)
    resources = [{"id": "new", "pipeline_id": "run-1"}]

    asyncio.run(
        insert_genomic_resource(
            db,
            sample_id="sample-1",
            pipeline_id="run-1",
            resource_data=resources,
        )
    )

    collection.update_one.assert_awaited_once_with(
        {"sample_id": "sample-1"},
        {"$push": {"genomic_resources": {"$each": resources}}},
        session=None,
    )
