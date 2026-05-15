"""Generic database functions."""

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Any

import bonsai_api
from api_client.audit_log import AuditLogClient
from api_client.audit_log.models import EventCreate, EventSeverity, Subject
from api_client.core.exceptions import ApiRequestError
from bonsai_api.db import Database
from bonsai_api.exceptions import AuditLogError
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
            try:
                audit.post_event(event)
            except ApiRequestError as exc:
                raise AuditLogError(
                    f"Audit log event failed for {event_type}: {exc}"
                ) from exc


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
