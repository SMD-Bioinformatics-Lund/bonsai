"""New metadata uploads must be stored in the format used by sample responses."""

import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import patch

from bonsai_libs.api_client.audit_log.models import Actor, SourceType
from bonsai_api.crud.metadata import add_metadata_to_sample
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.metadata import InputTableMetadata
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
