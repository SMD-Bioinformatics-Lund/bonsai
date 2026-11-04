"""Sample-ingestion integrity checks, runnable without extra test dependencies.

Run with ``python -m unittest discover -s tests/ingestion -v`` from api/.
Set BONSAI_TEST_MONGODB_URI only for a disposable MongoDB instance to also run
the real-index checks. Those checks create and delete uniquely named test DBs.
"""

import asyncio
import logging
import os
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from bonsai_libs.api_client.audit_log.models import Actor, SourceType
from bonsai_api.db.db import MongoDatabase
from bonsai_api.db.index import INDEXES, SAMPLE_RUN_LIMS_INDEX
from bonsai_api.dependencies import (
    get_audit_log,
    get_current_active_user,
    get_database,
    get_request_context,
)
from bonsai_api.exceptions import ConflictError
from bonsai_api.internal.error_handlers import register_exception_handlers
from bonsai_api.main import ensure_database_setup
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.sample import SampleInfoCreate, SequencingInfo
from bonsai_api.routers.samples import samples as sample_routes
from bonsai_api.services import sample_service
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError, OperationFailure


def setUpModule():
    root_logger = logging.getLogger()
    unittest.addModuleCleanup(root_logger.setLevel, root_logger.level)
    root_logger.setLevel(logging.WARNING)


def sample_input(lims_id="CLARITY-1", run_id="RUN-1"):
    return SampleInfoCreate(
        sample_id="LAB-1",
        sample_name="Test sample",
        lims_id=lims_id,
        sequencing={"platform": "illumina", "sequencing_run_id": run_id},
    )


def request_context():
    return ApiRequestContext(
        actor=Actor(id="test-uploader", type=SourceType.USR), metadata={}
    )


@asynccontextmanager
async def no_transaction(client, session=None):
    """Isolate index/error checks from transaction and auditing dependencies."""
    yield session


def duplicate_pair_error():
    return DuplicateKeyError(
        "Duplicate sample identifiers",
        11000,
        {"keyPattern": dict(SAMPLE_RUN_LIMS_INDEX["definition"])},
    )


class SampleIdentifierTests(unittest.TestCase):
    def test_missing_null_and_blank_identifiers_are_absent(self):
        for value in (None, "", " \t\n"):
            with self.subTest(value=value):
                sample = sample_input(value, value)
                self.assertIsNone(sample.lims_id)
                self.assertIsNone(sample.sequencing.sequencing_run_id)
                doc = sample.model_dump(exclude_none=True)
                self.assertNotIn("lims_id", doc)
                self.assertNotIn("sequencing_run_id", doc["sequencing"])
        self.assertIsNone(SequencingInfo(platform="illumina").sequencing_run_id)
        self.assertIsNone(
            SampleInfoCreate(sample_id="LAB-1", sample_name="Test").sequencing
        )

    def test_non_blank_identifiers_are_preserved_exactly(self):
        sample = sample_input(" Clarity-1 ", " Run-1 ")
        self.assertEqual(sample.lims_id, " Clarity-1 ")
        self.assertEqual(sample.sequencing.sequencing_run_id, " Run-1 ")

    def test_invalid_identifier_types_are_still_rejected(self):
        for lims, run in ((42, "RUN-1"), ("CLARITY-1", 42)):
            with self.subTest(lims=lims, run=run):
                with self.assertRaises(ValidationError):
                    sample_input(lims, run)

    def test_duplicate_pair_is_reported_as_http_409(self):
        app = FastAPI()
        app.include_router(sample_routes.router)
        register_exception_handlers(app)
        app.dependency_overrides[get_database] = lambda: SimpleNamespace(client=None)
        app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace()
        app.dependency_overrides[get_audit_log] = lambda: None
        app.dependency_overrides[get_request_context] = request_context
        insert = AsyncMock(side_effect=duplicate_pair_error())
        with (
            patch.object(sample_service, "managed_transaction", no_transaction),
            patch.object(sample_service, "insert_sample_document", insert),
            TestClient(app) as client,
        ):
            response = client.post(
                "/samples/", json=sample_input().model_dump(mode="json")
            )
        self.assertEqual(response.status_code, 409)
        self.assertIn("CLARITY-1", response.json()["detail"])
        self.assertIn("RUN-1", response.json()["detail"])


class SampleCreationAndStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_named_index_error_also_identifies_the_pair(self):
        name = SAMPLE_RUN_LIMS_INDEX["options"]["name"]
        insert = AsyncMock(side_effect=DuplicateKeyError(f"E11000 index: {name}"))
        with (
            patch.object(sample_service, "managed_transaction", no_transaction),
            patch.object(sample_service, "insert_sample_document", insert),
        ):
            with self.assertRaisesRegex(
                ConflictError, "Clarity/LIMS ID.*CLARITY-1.*RUN-1"
            ):
                await sample_service.create_sample_service(
                    SimpleNamespace(client=None),
                    sample=sample_input(),
                    ctx=request_context(),
                )

    async def test_other_unique_index_errors_do_not_claim_a_pair_conflict(self):
        insert = AsyncMock(side_effect=DuplicateKeyError("E11000 index: _id_"))
        with (
            patch.object(sample_service, "managed_transaction", no_transaction),
            patch.object(sample_service, "insert_sample_document", insert),
        ):
            with self.assertRaisesRegex(ConflictError, "same unique identifier"):
                await sample_service.create_sample_service(
                    SimpleNamespace(client=None),
                    sample=sample_input(),
                    ctx=request_context(),
                )

    async def test_normalized_identifiers_are_persisted_with_a_new_uid(self):
        insert = AsyncMock(return_value=SimpleNamespace(inserted_id="mongo-id"))
        with (
            patch.object(sample_service, "managed_transaction", no_transaction),
            patch.object(sample_service, "insert_sample_document", insert),
        ):
            result = await sample_service.create_sample_service(
                SimpleNamespace(client=None),
                sample=sample_input("", " \t"),
                ctx=request_context(),
            )
        doc = insert.call_args.kwargs["doc"]
        self.assertNotIn("lims_id", doc)
        self.assertNotIn("sequencing_run_id", doc["sequencing"])
        self.assertEqual(doc["sample_id"], result["internal_sample_id"])
        self.assertNotEqual(doc["sample_id"], "LAB-1")

    async def test_required_index_failure_aborts_database_setup(self):
        collection = SimpleNamespace(
            create_index=AsyncMock(side_effect=OperationFailure("duplicates"))
        )
        db = SimpleNamespace(sample_collection=collection)
        with patch.dict(INDEXES, {"sample": [SAMPLE_RUN_LIMS_INDEX]}, clear=True):
            with self.assertRaisesRegex(
                RuntimeError, "Required database index"
            ) as raised:
                await ensure_database_setup(db)
        self.assertIsInstance(raised.exception.__cause__, OperationFailure)
        collection.create_index.assert_awaited_once_with(
            SAMPLE_RUN_LIMS_INDEX["definition"], **SAMPLE_RUN_LIMS_INDEX["options"]
        )

    async def test_optional_performance_index_failure_still_only_warns(self):
        collection = SimpleNamespace(
            create_index=AsyncMock(side_effect=OperationFailure("unavailable"))
        )
        db = SimpleNamespace(sample_collection=collection)
        optional_index = INDEXES["sample"][-1]
        with patch.dict(INDEXES, {"sample": [optional_index]}, clear=True):
            await ensure_database_setup(db)


@unittest.skipUnless(
    os.environ.get("BONSAI_TEST_MONGODB_URI"), "requires disposable MongoDB"
)
class MongoSampleUniquenessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncMongoClient(
            os.environ["BONSAI_TEST_MONGODB_URI"], serverSelectionTimeoutMS=5000
        )
        self.addAsyncCleanup(self.client.close)
        self.db_name = f"bonsai_uniqueness_test_{uuid4().hex}"
        self.addAsyncCleanup(self.client.drop_database, self.db_name)
        self.db = MongoDatabase()
        self.db.setup(self.client, self.db_name)
        self.collection = self.db.sample_collection
        for index in INDEXES["sample"]:
            await self.collection.create_index(index["definition"], **index["options"])
        transaction_patch = patch.object(
            sample_service, "managed_transaction", no_transaction
        )
        transaction_patch.start()
        self.addCleanup(transaction_patch.stop)

    async def create(self, lims="CLARITY-1", run="RUN-1"):
        return await sample_service.create_sample_service(
            self.db, sample=sample_input(lims, run), ctx=request_context()
        )

    async def test_concurrent_duplicate_uploads_create_only_one_record(self):
        results = await asyncio.gather(
            self.create(), self.create(), return_exceptions=True
        )
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        errors = [result for result in results if isinstance(result, ConflictError)]
        self.assertEqual(len(errors), 1)
        self.assertIn("CLARITY-1", str(errors[0]))
        self.assertIn("RUN-1", str(errors[0]))
        self.assertEqual(await self.collection.count_documents({}), 1)

    async def test_different_runs_or_clarity_ids_remain_allowed(self):
        results = [
            await self.create(),
            await self.create(run="RUN-2"),
            await self.create(lims="CLARITY-2"),
        ]
        self.assertEqual(len({result["internal_sample_id"] for result in results}), 3)
        self.assertEqual(await self.collection.count_documents({}), 3)

    async def test_incomplete_pairs_allow_repeated_uploads(self):
        count = 0
        for lims, run in (
            ("CLARITY-1", None),
            ("CLARITY-1", ""),
            ("CLARITY-1", " \t"),
            (None, "RUN-1"),
            ("", "RUN-1"),
            (" \t", "RUN-1"),
        ):
            for _ in range(2):
                await self.create(lims, run)
                count += 1
        self.assertEqual(await self.collection.count_documents({}), count)

    async def test_index_excludes_missing_null_and_empty_fields_directly(self):
        cases = [
            {"lims_id": "CLARITY-1"},
            {"lims_id": "CLARITY-1", "sequencing": {"sequencing_run_id": None}},
            {"lims_id": "CLARITY-1", "sequencing": {"sequencing_run_id": ""}},
            {"sequencing": {"sequencing_run_id": "RUN-1"}},
            {"lims_id": None, "sequencing": {"sequencing_run_id": "RUN-1"}},
            {"lims_id": "", "sequencing": {"sequencing_run_id": "RUN-1"}},
        ]
        for case in cases:
            for _ in range(2):
                await self.collection.insert_one({"sample_id": str(uuid4()), **case})
        self.assertEqual(await self.collection.count_documents({}), 12)

    async def test_existing_duplicates_abort_setup_without_deleting_records(self):
        await self.collection.drop_index(SAMPLE_RUN_LIMS_INDEX["options"]["name"])
        await self.create()
        await self.create()
        with self.assertRaisesRegex(RuntimeError, "Required database index"):
            await ensure_database_setup(self.db)
        self.assertEqual(await self.collection.count_documents({}), 2)


if __name__ == "__main__":
    unittest.main()
