"""Generic database functions."""

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Any

import bonsai_api
from api_client.audit_log import AuditLogClient
from api_client.audit_log.models import EventCreate, EventSeverity, Subject
from bonsai_api.db import Database
from bonsai_api.models.context import ApiRequestContext
from pymongo import AsyncMongoClient
from pymongo.client_session import ClientSession
from pymongo.collection import Collection

LOG = logging.getLogger(__name__)


async def get_deprecated_records(
    collection: Collection, schema_version: int
) -> list[dict[str, Any]]:
    """Get documents from the collection that have a schema version."""
    cursor = collection.find(
        {
            "$or": [
                {"schema_version": {"$lt": schema_version}},
                {"schema_version": {"$exists": False}},
            ]
        }
    )
    return [dict(doc) for doc in await cursor.to_list(None)]


@contextmanager
def audit_event_context(
    audit: AuditLogClient | None,
    event_type: str,
    ctx: ApiRequestContext,
    subject: Subject,
    metadata: dict[str, Any] | None = None,
):
    """Logg an event to the audit log."""
    exc = None
    try:
        yield
    except Exception as e:
        exc = e
        raise
    finally:
        if isinstance(audit, AuditLogClient):
            meta = dict(metadata) if metadata else {}
            severity = EventSeverity.ERROR if exc else EventSeverity.INFO
            if exc:
                meta["exception"] = str(exc)
            event = EventCreate(
                source_service=bonsai_api.__name__,
                event_type=event_type,
                severity=severity,
                actor=ctx.actor,
                subject=subject,
                metadata=meta,
            )
            audit.post_event(event)


async def check_groups_exists(
    db: Database, *, group_ids: list[str], session: Any = None
) -> list[str]:
    """Check if group with group_id exists in database.

    Return missing group ids.
    """
    if not group_ids:
        return []

    if not isinstance(group_ids, list):
        raise RuntimeError(f"Invalid input data, expect list[str] but got: {group_ids}")

    existing = await db.sample_group_collection.find(
        {"group_id": {"$in": group_ids}}, {"group_id": 1, "_id": 0}, session=session
    ).to_list(None)

    existing_ids: set[str] = {gr["group_id"] for gr in existing}
    missing = set(group_ids) - existing_ids
    if missing:
        LOG.warning("Did not find groups: %s", missing)
    return missing


async def check_samples_exists(
    db: Database, *, sample_ids: list[str], session: Any = None
) -> list[str]:
    """Check if group with group_id exists in database.

    Return missing group ids.
    """
    if not sample_ids:
        return []

    if not isinstance(sample_ids, list):
        raise RuntimeError(
            f"Invalid input data, expect list[str] but got: {sample_ids}"
        )

    existing = await db.sample_collection.find(
        {"sample_id": {"$in": sample_ids}}, {"sample_id": 1, "_id": 0}, session=session
    ).to_list(None)

    existing_ids: set[str] = {gr["sample_id"] for gr in existing}
    missing = set(sample_ids) - existing_ids
    if missing:
        LOG.warning("Did not find samples: %s", missing)
    return missing


async def check_user_exists(db: Database, *, user_id: str, session: Any = None) -> bool:
    """Check if user with user_id exists in database."""
    user = await db.user_collection.find_one(
        {"username": user_id}, {"_id": 1}, session=session
    )
    return user is not None


@asynccontextmanager
async def managed_transaction(
    client: AsyncMongoClient, session: ClientSession | None = None
):
    """Yields a session,

    It performs open/ close and starting transaction only if needed."""
    if session is not None:
        # If a caller provided a session/ transactipn; just yield it.
        yield session
        return

    async with client.start_session() as sess:
        txn = await sess.start_transaction()
        async with txn:
            yield sess
