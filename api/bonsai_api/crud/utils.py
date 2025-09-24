"""Generic database functions."""

from typing import Any
from motor.motor_asyncio import AsyncIOMotorCollection
from contextlib import contextmanager

from bonsai_api.models.context import ApiRequestContext

import bonsai_api
from api_client.audit_log import AuditLogClient
from api_client.audit_log.models import Subject, EventSeverity, EventCreate

async def get_deprecated_records(collection: AsyncIOMotorCollection, schema_version: int) -> list[dict[str, Any]]:
    """Get documents from the collection that have a schema version."""
    cursor = collection.find({"$or": [
        {"schema_version": {"$lt": schema_version}},
        {"schema_version": {"$exists": False}}
    ]})
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
                meta['exception'] = str(exc)
            event = EventCreate(
                source_service=bonsai_api.__name__,
                event_type=event_type,
                severity=severity,
                actor=ctx.actor,
                subject=subject,
                metadata=meta,
            )
            audit.post_event(event)
