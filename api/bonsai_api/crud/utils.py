"""Generic database functions."""

import logging

from contextlib import asynccontextmanager, contextmanager
from typing import Any
from pymongo import AsyncMongoClient
from pymongo.collection import Collection
from pymongo.client_session import ClientSession

import bonsai_api
from bonsai_api.db import Database
from api_client.audit_log import AuditLogClient
from api_client.audit_log.models import EventCreate, EventSeverity, Subject
from bonsai_api.models.context import ApiRequestContext


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


async def check_groups_exists(db: Database, group_ids: list[str], session: Any = None) -> list[str]:
    """Check if group with group_id exists in database.
    
    Return missing group ids.
    """
    if not group_ids:
        return False

    existing = await db.sample_group_collection.find(
        {"group_id": {"$in": group_ids}}, {"group_id": 1, "_id": 0}, session=session
    ).to_list(None)

    existing_ids: set[str] = {gr["group_id"] for gr in existing}
    missing = set(group_ids) - existing_ids
    if missing:
        LOG.warning("Did not find groups: %s", missing)
    return len(missing) == 0


@asynccontextmanager
async def managed_transaction(client: AsyncMongoClient, session: ClientSession | None = None):
    """Yields a session, 

    It performs open/ close and starting transaction only if needed."""
    if session is not None:
        # If a caller provided a session/ transactipn; just yield it.
        yield session
        return
    
    async with client.start_session() as sess:
        async with sess.start_transaction():
            yield sess
