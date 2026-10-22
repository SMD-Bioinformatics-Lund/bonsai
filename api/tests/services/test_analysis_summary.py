"""Backfill the SDK's STX display field without changing the supporting data."""

import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest
from mongomock_motor import AsyncMongoMockClient

from bonsai_api.services.analysis_summary import backfill_typing_summaries


def hit(symbol):
    return {
        "gene_symbol": symbol,
        "element_type": "VIRULENCE",
        "element_subtype": "VIRULENCE",
    }


def test_backfill_dry_run_apply_and_repeat_preserve_sample_data():
    async def run():
        collection = AsyncMongoMockClient().test.samples
        db = SimpleNamespace(sample_collection=collection)
        sample = {
            "sample_id": "sample-1",
            "modified_at": "unchanged",
            "comments": [{"comment": "Keep me"}],
            "typing_result": [
                {
                    "software": "virulencefinder",
                    "analysis_type": "stx",
                    "result": {"hits": [hit("stx2a"), hit("stx1a")]},
                    "summary": {"other": "Keep me"},
                    "curations": [{"comment": "Keep me"}],
                },
                {
                    "software": "serotypefinder",
                    "analysis_type": "o_type",
                    "result": {"sequence_name": "O157"},
                },
                {
                    "software": "mlst",
                    "analysis_type": "mlst",
                    "result": {"sequence_type": 11},
                },
            ],
        }
        await collection.insert_one(sample)
        original = await collection.find_one()
        assert await backfill_typing_summaries(db, dry_run=True) == {
            "pending": 1,
            "updated": 0,
            "conflicts": 0,
        }
        assert await collection.find_one() == original

        assert await backfill_typing_summaries(db) == {
            "pending": 1,
            "updated": 1,
            "conflicts": 0,
        }
        expected = deepcopy(original)
        expected["typing_result"][0]["result"]["gene_symbol"] = "stx2a, stx1a"
        assert await collection.find_one() == expected
        assert await backfill_typing_summaries(db) == {
            "pending": 0,
            "updated": 0,
            "conflicts": 0,
        }

    asyncio.run(run())


@pytest.mark.parametrize(
    "result,status,expected,updated",
    [
        (hit("stx1a"), "parsed", hit("stx1a"), 0),
        (
            {"hits": [hit("stx2a")]},
            "parsed",
            {"hits": [hit("stx2a")], "gene_symbol": "stx2a"},
            1,
        ),
        (
            {"hits": [hit("stx2a")]},
            "absent",
            {"hits": [hit("stx2a")]},
            0,
        ),
    ],
)
def test_backfill_single_object_source(result, status, expected, updated):
    async def run():
        collection = AsyncMongoMockClient().test.samples
        await collection.insert_one(
            {
                "typing_result": {
                    "software": "virulencefinder",
                    "analysis_type": "stx",
                    "status": status,
                    "result": result,
                }
            }
        )
        counts = await backfill_typing_summaries(
            SimpleNamespace(sample_collection=collection)
        )
        assert counts == {"pending": updated, "updated": updated, "conflicts": 0}
        stored = await collection.find_one()
        assert stored["typing_result"]["result"] == expected

    asyncio.run(run())


def test_backfill_skips_a_concurrent_result_replacement():
    async def run():
        collection = AsyncMongoMockClient().test.samples
        await collection.insert_one(
            {
                "typing_result": [
                    {
                        "software": "virulencefinder",
                        "analysis_type": "stx",
                        "result": {"hits": [hit("stx1a")]},
                    }
                ]
            }
        )

        async def concurrent_update(query, update):
            await collection.update_one(
                {"_id": query["_id"]},
                {"$set": {"typing_result.0.result": hit("stx2a")}},
            )
            return await collection.update_one(query, update)

        db = SimpleNamespace(
            sample_collection=SimpleNamespace(
                find=collection.find, update_one=concurrent_update
            )
        )
        assert await backfill_typing_summaries(db) == {
            "pending": 1,
            "updated": 0,
            "conflicts": 1,
        }
        stored = await collection.find_one()
        assert stored["typing_result"][0]["result"] == hit("stx2a")
        assert "summary" not in stored["typing_result"][0]

    asyncio.run(run())
