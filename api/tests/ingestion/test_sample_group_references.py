"""Regression checks for group references accepted by POST /samples/."""

import asyncio
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bonsai_libs.api_client.audit_log.models import Actor, SourceType
from bonsai_api.dependencies import (
    get_audit_log,
    get_current_active_user,
    get_database,
    get_request_context,
)
from bonsai_api.internal.error_handlers import register_exception_handlers
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.routers.samples import samples as sample_routes
from bonsai_api.services import sample_service
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient


GROUP_ID = "01a0e75d-d435-7ca3-8719-4a2aaa0353ac"


@asynccontextmanager
async def no_transaction(client, session=None):
    yield session


class SampleGroupReferenceTests(unittest.TestCase):
    def setUp(self):
        client = AsyncMongoMockClient()
        self.db = SimpleNamespace(
            client=client, sample_group_collection=client.test.sample_group
        )
        asyncio.run(
            self.db.sample_group_collection.insert_one(
                {"core": {"group_id": GROUP_ID, "group_key": "test_key"}}
            )
        )
        app = FastAPI()
        app.include_router(sample_routes.router)
        register_exception_handlers(app)
        app.dependency_overrides[get_database] = lambda: self.db
        app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace()
        app.dependency_overrides[get_audit_log] = lambda: None
        app.dependency_overrides[get_request_context] = lambda: ApiRequestContext(
            actor=Actor(id="test-uploader", type=SourceType.USR), metadata={}
        )
        self.insert = AsyncMock(return_value=SimpleNamespace(inserted_id="mongo-id"))
        self.memberships = AsyncMock()
        for name, replacement in (
            ("managed_transaction", no_transaction),
            ("insert_sample_document", self.insert),
            ("add_memberships", self.memberships),
        ):
            patcher = patch.object(sample_service, name, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = self.enterContext(TestClient(app))

    def create(self, groups):
        return self.client.post(
            "/samples/",
            json={
                "sample_id": "sample_id_2",
                "sample_name": "sample_name_2",
                "groups": groups,
            },
        )

    def test_ids_keys_and_duplicate_references_use_internal_memberships(self):
        for references in ([GROUP_ID], ["test_key"], ["test_key", GROUP_ID, "test_key"]):
            with self.subTest(references=references):
                self.memberships.reset_mock()
                response = self.create(references)
                self.assertEqual(response.status_code, 201, response.text)
                edges = self.memberships.call_args.kwargs["edges"]
                self.assertEqual([edge.group_id for edge in edges], [GROUP_ID])
                self.assertEqual(edges[0].sample_id, response.json()["internal_sample_id"])
                self.assertNotEqual(edges[0].sample_id, "sample_id_2")

    def test_unknown_reference_is_rejected_before_sample_insertion(self):
        response = self.create(["test_key", "missing_key"])
        self.assertEqual(response.status_code, 404, response.text)
        self.assertIn("missing_key", response.json()["detail"])
        self.insert.assert_not_awaited()
        self.memberships.assert_not_awaited()

    def test_empty_groups_still_allow_sample_creation(self):
        response = self.create([])
        self.assertEqual(response.status_code, 201, response.text)
        self.memberships.assert_not_awaited()

    def test_internal_id_takes_precedence_over_another_groups_key(self):
        asyncio.run(
            self.db.sample_group_collection.insert_one(
                {"core": {"group_id": "another-group-id", "group_key": GROUP_ID}}
            )
        )
        response = self.create([GROUP_ID])
        self.assertEqual(response.status_code, 201, response.text)
        edges = self.memberships.call_args.kwargs["edges"]
        self.assertEqual([edge.group_id for edge in edges], [GROUP_ID])
