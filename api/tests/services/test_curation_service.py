"""Tests for curation service synchronization."""

from types import SimpleNamespace
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock
from datetime import datetime

import pytest
from mongomock_motor import AsyncMongoMockClient
from pymongo.errors import DuplicateKeyError
from bonsai_api.exceptions import ConflictError, EntryNotFound, AuditLogError
from bonsai_api.models.analysis import VariantCurationUpdate, VariantCurationCreate
from bonsai_libs.api_client.audit_log import AuditLogClient
from bonsai_libs.api_client.audit_log.models import Actor
from bonsai_libs.api_client.core.exceptions import ApiError
from bonsai_api.services import curation_service


@pytest.mark.asyncio
async def test_sync_clears_included_analysis_type_when_only_other_type_remains(
    monkeypatch,
):
    """A deleted type is cleared while another type remains curated."""
    monkeypatch.setattr(
        curation_service,
        "get_curations_crud",
        AsyncMock(
            return_value=[
                {
                    "sample_id": "sample-1",
                    "analysis_id": "analysis-1",
                    "analysis_type": "cgmlst",
                    "decision": "accept",
                }
            ]
        ),
    )
    monkeypatch.setattr(
        curation_service,
        "UpdateOne",
        lambda filter_, update: (filter_, update),
    )

    bulk_write = AsyncMock(
        return_value=SimpleNamespace(matched_count=1, acknowledged=True)
    )
    db = SimpleNamespace(sample_collection=SimpleNamespace(bulk_write=bulk_write))

    result = await curation_service.sync_curation_summary_for_analysis(
        db,
        sample_id="sample-1",
        analysis_id="analysis-1",
        include_analysis_types={"amr"},
    )

    operations = bulk_write.await_args.args[0]
    assert (
        {
            "sample_id": "sample-1",
            "element_type_result": {
                "$elemMatch": {
                    "analysis_id": "analysis-1",
                    "analysis_type": "amr",
                }
            },
        },
        {"$set": {"element_type_result.$.curations": []}},
    ) in operations
    assert result is True


@asynccontextmanager
async def _transaction(_client):
    yield None


@pytest.fixture
def curation_db(monkeypatch):
    monkeypatch.setattr(curation_service, "managed_transaction", _transaction)
    monkeypatch.setattr(curation_service, "sync_curation_summary_for_analysis", AsyncMock())
    return SimpleNamespace(
        client=None, curations_collection=AsyncMongoMockClient().db.curations,
    )


def _curation():
    return {
        "id": "curation-1", "sample_id": "sample-1", "analysis_id": "analysis-1",
        "analysis_type": "amr", "annotation_type": "variant", "result_key": "0",
        "decision": "reject", "rejection_reason": "Old reason",
        "phenotypes": [{"name": "old drug", "meta": {"resistance_level": "high"}}],
        "curated_by": "first-user", "approved_by": "approver",
        "created_at": datetime(2025, 1, 1), "modified_at": datetime(2025, 1, 1),
        "notes": "Keep these notes", "comment": "Keep this comment", "tags": ["checked"],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("decision", ["accept", "reject"])
async def test_update_preserves_identity_replaces_annotations_and_clears_approval(curation_db, decision):
    original = _curation()
    await curation_db.curations_collection.insert_one(dict(original))
    audit = Mock(spec=AuditLogClient)
    update = VariantCurationUpdate(
        decision=decision, rejection_reason="New reason",
        phenotypes=[{"name": "new drug", "meta": {"resistance_level": "low"}}],
    )

    await curation_service.update_variant_curation_service(
        curation_db, curation_id="curation-1", curation=update,
        curated_by="second-user", ctx=SimpleNamespace(actor=Actor(type="user", id="second-user")),
        audit=audit,
    )

    saved = await curation_db.curations_collection.find_one({"id": "curation-1"})
    for key in ("id", "analysis_id", "analysis_type", "annotation_type", "sample_id", "result_key", "created_at", "notes", "comment", "tags"):
        assert saved[key] == original[key]
    assert saved["decision"] == decision
    assert saved["phenotypes"] == update.model_dump()["phenotypes"]
    assert saved["curated_by"] == "second-user"
    assert saved["approved_by"] is None
    assert saved["modified_at"] > original["modified_at"]
    assert saved["rejection_reason"] == ("New reason" if decision == "reject" else None)
    assert await curation_db.curations_collection.count_documents({}) == 1
    curation_service.sync_curation_summary_for_analysis.assert_awaited_once_with(
        curation_db, sample_id="sample-1", analysis_id="analysis-1", session=None,
    )
    event = audit.post_event.call_args.args[0]
    assert event.event_type == "update_curation"
    assert event.actor.id == "second-user"
    assert event.metadata["before"]["curated_by"] == "first-user"
    assert event.metadata["after"]["curated_by"] == "second-user"
    assert event.metadata["before"]["decision"] == "reject"
    assert event.metadata["before"]["approved_by"] == "approver"
    assert event.metadata["after"]["phenotypes"] == saved["phenotypes"]


@pytest.mark.asyncio
async def test_approval_preserves_curator_and_records_approval_author(curation_db):
    original = {**_curation(), "approved_by": None}
    await curation_db.curations_collection.insert_one(dict(original))
    audit = Mock(spec=AuditLogClient)

    await curation_service.approve_curation_service(
        curation_db, curation_id="curation-1", approved_by="reviewer",
        ctx=SimpleNamespace(actor=Actor(type="user", id="reviewer")), audit=audit,
    )

    saved = await curation_db.curations_collection.find_one({"id": "curation-1"})
    assert saved["curated_by"] == original["curated_by"]
    assert saved["created_at"] == original["created_at"]
    assert saved["decision"] == original["decision"]
    assert saved["phenotypes"] == original["phenotypes"]
    assert saved["approved_by"] == "reviewer"
    assert saved["modified_at"] > original["modified_at"]
    curation_service.sync_curation_summary_for_analysis.assert_awaited_once_with(
        curation_db, sample_id="sample-1", analysis_id="analysis-1", session=None,
    )
    event = audit.post_event.call_args.args[0]
    assert event.event_type == "approve_curation"
    assert event.actor.id == "reviewer"
    assert event.metadata["approved_by"] == "reviewer"


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", [True, False])
async def test_update_rejects_missing_or_non_variant_curation(curation_db, missing):
    if not missing:
        await curation_db.curations_collection.insert_one({**_curation(), "annotation_type": "gene"})
    with pytest.raises(EntryNotFound if missing else ConflictError):
        await curation_service.update_variant_curation_service(
            curation_db, curation_id="curation-1", curation=VariantCurationUpdate(decision="accept"),
            curated_by="user", ctx=None,
        )
    curation_service.sync_curation_summary_for_analysis.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_still_rejects_duplicates(curation_db, monkeypatch):
    monkeypatch.setattr(curation_service, "get_analysis_service", AsyncMock(
        return_value=SimpleNamespace(sample_id="sample-1", envelopes={"amr": {}})
    ))
    monkeypatch.setattr(curation_service, "create_curation", AsyncMock(side_effect=DuplicateKeyError("duplicate")))
    with pytest.raises(ConflictError, match="Curation already exists"):
        await curation_service.create_curation_service(
            curation_db, analysis_id="analysis-1", analysis_type="amr",
            curation=VariantCurationCreate(result_key="0", decision="accept", phenotypes=[]),
            curated_by="user", ctx=None,
        )


@pytest.mark.asyncio
async def test_remove_clears_summary_and_audits_the_removed_annotations(curation_db):
    await curation_db.curations_collection.insert_one(_curation())
    audit = Mock(spec=AuditLogClient)
    await curation_service.delete_curation_service(
        curation_db, curation_id="curation-1", deleted_by="second-user",
        ctx=SimpleNamespace(actor=Actor(type="user", id="second-user")), audit=audit,
    )
    assert await curation_db.curations_collection.count_documents({}) == 0
    curation_service.sync_curation_summary_for_analysis.assert_awaited_once_with(
        curation_db, sample_id="sample-1", analysis_id="analysis-1",
        include_analysis_types={"amr"}, session=None,
    )
    event = audit.post_event.call_args.args[0]
    assert event.event_type == "delete_curation"
    assert event.actor.id == "second-user"
    assert event.metadata["deleted_by"] == "second-user"
    assert event.metadata["curation"]["decision"] == "reject"
    assert event.metadata["curation"]["phenotypes"] == _curation()["phenotypes"]
    assert "_id" not in event.metadata["curation"]


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["update", "delete"])
async def test_audit_failure_prevents_transaction_commit(curation_db, monkeypatch, action):
    committed = []

    @asynccontextmanager
    async def transaction(_client):
        yield None
        committed.append(True)

    monkeypatch.setattr(curation_service, "managed_transaction", transaction)
    await curation_db.curations_collection.insert_one(_curation())
    audit = Mock(spec=AuditLogClient)
    audit.post_event.side_effect = ApiError("Audit unavailable")
    with pytest.raises(AuditLogError):
        context = SimpleNamespace(actor=Actor(type="user", id="user"))
        if action == "update":
            await curation_service.update_variant_curation_service(
                curation_db, curation_id="curation-1", curation=VariantCurationUpdate(decision="accept"),
                curated_by="user", ctx=context, audit=audit,
            )
        else:
            await curation_service.delete_curation_service(
                curation_db, curation_id="curation-1", deleted_by="user", ctx=context, audit=audit,
            )
    assert not committed
