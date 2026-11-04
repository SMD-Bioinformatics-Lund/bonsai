"""External IDs may identify several sequencing records, never an arbitrary one."""

import asyncio
import unittest
from types import SimpleNamespace
from uuid import uuid4

from bonsai_api.dependencies import get_current_active_user, get_database
from bonsai_api.internal.error_handlers import register_exception_handlers
from bonsai_api.models.sample import SampleRecordDb
from bonsai_api.routers.samples import samples as sample_routes
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient


class ExternalSampleLookupTests(unittest.TestCase):
    def setUp(self):
        self.collection = AsyncMongoMockClient().test.samples
        app = FastAPI()
        app.include_router(sample_routes.router)
        register_exception_handlers(app)
        app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace()
        app.dependency_overrides[get_database] = lambda: SimpleNamespace(
            sample_collection=self.collection
        )
        self.client = self.enterContext(TestClient(app))

    def add_sample(self, run="RUN-1", external_id="LAB-123"):
        record = SampleRecordDb(
            sample_id=str(uuid4()),
            external_sample_id=external_id,
            sample_name="Repeated sample name",
            sequencing={"platform": "illumina", "sequencing_run_id": run},
        )
        asyncio.run(self.collection.insert_one(record.model_dump()))
        return record.sample_id

    def test_unique_external_id_keeps_existing_lookup_behavior(self):
        expected = self.add_sample()
        self.add_sample(external_id="LAB-other")
        response = self.client.get("/samples/external/LAB-123")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sample_id"], expected)

    def test_duplicate_external_id_returns_conflict(self):
        self.add_sample()
        self.add_sample(run="RUN-2")
        response = self.client.get("/samples/external/LAB-123")
        self.assertEqual(response.status_code, 409)
        self.assertIn("internal sample ID", response.json()["detail"])

    def test_ambiguity_within_the_same_run_still_returns_conflict(self):
        self.add_sample()
        self.add_sample()
        response = self.client.get("/samples/external/LAB-123")
        self.assertEqual(response.status_code, 409)

    def test_unknown_external_id_returns_not_found(self):
        self.add_sample()
        response = self.client.get("/samples/external/unknown")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
