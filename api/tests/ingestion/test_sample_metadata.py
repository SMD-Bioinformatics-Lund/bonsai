"""New metadata uploads must be stored in the format used by sample responses."""

import asyncio
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import patch

from bonsai_libs.api_client.audit_log.models import Actor, SourceType
from bonsai_api.crud.metadata import add_metadata_to_sample
from bonsai_api.exceptions import EntryNotFound
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.metadata import GenericMetadataEntry, InputTableMetadata
from bonsai_api.models.sample import SampleInfoCreate, SampleRecordDb, SampleRecordOut
from bonsai_api.services import sample_service
from mongomock_motor import AsyncMongoMockClient


@asynccontextmanager
async def no_transaction(client, session=None):
    yield session


class SampleMetadataTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_and_append_store_readable_tables_with_empty_cells(self):
        collection = AsyncMongoMockClient().test.samples
        db = SimpleNamespace(client=None, sample_collection=collection)
        scalar = {
            "fieldname": "country",
            "category": "general",
            "type": "string",
            "value": "Sweden",
        }
        sample = SampleInfoCreate(
            sample_id="LAB-1",
            sample_name="Example",
            metadata=[
                scalar,
                {
                    "fieldname": "measurements",
                    "category": "results",
                    "type": "table",
                    "value": "name,count\nexample,\nother,2\n",
                },
            ],
        )
        ctx = ApiRequestContext(
            actor=Actor(id="test-uploader", type=SourceType.USR), metadata={}
        )
        with patch.object(sample_service, "managed_transaction", no_transaction):
            result = await sample_service.create_sample_service(db, sample=sample, ctx=ctx)

        sample_id = result["internal_sample_id"]
        doc = await collection.find_one({"sample_id": sample_id}, {"_id": 0})
        self.assertEqual(doc["metadata"][0], scalar)
        table = doc["metadata"][1]
        self.assertNotIn("value", table)
        self.assertEqual(table["columns"], ["name", "count"])
        self.assertEqual(table["data"], [["example", ""], ["other", 2.0]])
        original_metadata = doc["metadata"]

        await add_metadata_to_sample(
            sample_id,
            [InputTableMetadata(fieldname="extra", value="label,value\nmore,\n")],
            db,
        )
        doc = await collection.find_one({"sample_id": sample_id}, {"_id": 0})
        self.assertEqual(doc["metadata"][:2], original_metadata)
        self.assertEqual(doc["metadata"][2]["data"], [["more", ""]])
        for model in (SampleRecordDb, SampleRecordOut):
            with self.subTest(model=model.__name__):
                output = model.model_validate(doc)
                self.assertEqual(output.model_dump(mode="json")["metadata"], doc["metadata"])
                self.assertNotIn("NaN", output.model_dump_json())


class ConcurrentMetadataTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.collection = AsyncMongoMockClient().test.samples
        self.existing = self.entry("existing", "keep").model_dump()
        await self.collection.insert_one(
            {"sample_id": "sample-1", "metadata": [self.existing]}
        )
        self.db = SimpleNamespace(sample_collection=self.collection)

    @staticmethod
    def entry(name, value):
        return GenericMetadataEntry(
            fieldname=name, value=value, type="string", category="general"
        )

    async def append_concurrently(self, *batches):
        # Hold writes until every request has prepared its update. This also
        # reproduces lost additions if the old read/replace implementation returns.
        ready = asyncio.Event()
        waiting = 0

        async def synchronized_update(*args, **kwargs):
            nonlocal waiting
            waiting += 1
            if waiting == len(batches):
                ready.set()
            await asyncio.wait_for(ready.wait(), timeout=5)
            return await self.collection.update_one(*args, **kwargs)

        db = SimpleNamespace(sample_collection=SimpleNamespace(
            update_one=synchronized_update, find_one=self.collection.find_one
        ))
        return await asyncio.gather(
            *(add_metadata_to_sample("sample-1", batch, db) for batch in batches),
            return_exceptions=True,
        )

    async def stored_metadata(self):
        doc = await self.collection.find_one({"sample_id": "sample-1"})
        self.assertEqual(doc["metadata"][0], self.existing)
        return {entry["fieldname"]: entry["value"] for entry in doc["metadata"]}

    async def test_concurrent_distinct_fields_are_both_preserved(self):
        results = await self.append_concurrently(
            [self.entry("first", "one")], [self.entry("second", "two")]
        )
        self.assertEqual(results, [True, True])
        self.assertEqual(
            await self.stored_metadata(),
            {"existing": "keep", "first": "one", "second": "two"},
        )

    async def test_concurrent_duplicate_fields_allow_only_one_success(self):
        results = await self.append_concurrently(
            [self.entry("shared", "one")], [self.entry("shared", "two")]
        )
        self.assertEqual(sum(result is True for result in results), 1)
        self.assertEqual(sum(isinstance(result, FileExistsError) for result in results), 1)
        doc = await self.collection.find_one({"sample_id": "sample-1"})
        self.assertEqual(len(doc["metadata"]), 2)
        metadata = await self.stored_metadata()
        winner = "one" if results[0] is True else "two"
        self.assertEqual(metadata["shared"], winner)

    async def test_concurrent_overlapping_batches_reject_the_entire_losing_batch(self):
        results = await self.append_concurrently(
            [self.entry("shared", "one"), self.entry("only-first", "one")],
            [self.entry("shared", "two"), self.entry("only-second", "two")],
        )
        self.assertEqual(sum(result is True for result in results), 1)
        self.assertEqual(sum(isinstance(result, FileExistsError) for result in results), 1)
        winner = "first" if results[0] is True else "second"
        value = "one" if results[0] is True else "two"
        self.assertEqual(
            await self.stored_metadata(),
            {"existing": "keep", "shared": value, f"only-{winner}": value},
        )

    async def test_existing_field_conflict_does_not_append_other_fields(self):
        with self.assertRaises(FileExistsError):
            await add_metadata_to_sample(
                "sample-1",
                [self.entry("existing", "replace"), self.entry("new", "new")],
                self.db,
            )
        self.assertEqual(await self.stored_metadata(), {"existing": "keep"})

    async def test_missing_sample_raises_not_found(self):
        with self.assertRaises(EntryNotFound):
            await add_metadata_to_sample(
                "missing", [self.entry("new", "new")], self.db
            )
