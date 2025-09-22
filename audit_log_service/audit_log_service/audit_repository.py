"""Audit log repository."""

import logging
from typing import Any, Sequence
import datetime as dt
from bson import ObjectId
from pymongo import DESCENDING
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from .models import EventFilter, EventOut, PaginatedEvents
from audit_log_service.models import Event

LOG = logging.getLogger(__name__)


class AuditTrailRepository:
    """
    Store for audit log entries.

    Connection lifetime is managed outside of this class.
    Pass in a ready Collection (with auth, TLS, timeouts, etc. configured).
    """
    def __init__(self, collection: Collection[Any]):
        self._col = collection

    def log_event(self, event: Event) -> ObjectId | None:
        try:
            result = self._col.insert_one(event.model_dump())
            LOG.info("Audit event logged", extra={"id": str(result.inserted_id)})
            return result.inserted_id
        except PyMongoError as err:
            LOG.exception("Error logging audit event", extra={"error": err})
            raise
    
    def check_connection(self) -> bool:
        """Check database connection."""

        return bool(self._col.find_one())

    def get_events(self, *, limit: int = 50, skip: int = 0,
                   filters: EventFilter | None = None,
                   sort: Sequence[tuple[str, int]] | None = None) -> PaginatedEvents:
        """Get events from the database.

        - Default sort: newest first by occurred_at, then _id
        - Default limit: 50 (clamped to 1..500)
        """
        # Clamp pagination inputs
        if limit <= 0:
            limit = 1
        if limit > 500:
            limit = 500
        if skip < 0:
            skip = 0
        
        query: dict[str, Any] = {}

        # build mongodb query
        event_filter = filters or EventFilter()
        if event_filter.severities:
            query["severity"] = {"$in": event_filter.severities}

        if event_filter.event_types:
            query["event_type"] = {"$in": event_filter.event_types}

        if event_filter.source_services:
            query["source_service"] = {"$in": event_filter.source_services}

        if event_filter.actor_type:
            query["actor.type"] = event_filter.actor_type
        if event_filter.actor_id:
            query["actor.id"] = event_filter.actor_id

        if event_filter.subject_type:
            query["subject.type"] = event_filter.subject_type
        if event_filter.subject_id:
            query["subject.id"] = event_filter.subject_id

        # occurred_at range
        if event_filter.occurred_after or event_filter.occurred_before:
            dt_query: dict[str, Any] = {}
            if event_filter.occurred_after:
                # Ensure timezone-aware UTC
                dt_from = event_filter.occurred_after
                if dt_from.tzinfo is None:
                    dt_from = dt_from.replace(tzinfo=dt.timezone.utc)
                dt_query["$gte"] = dt_from
            if event_filter.occurred_before:
                dt_to = event_filter.occurred_before
                if dt_to.tzinfo is None:
                    dt_to = dt_to.replace(tzinfo=dt.timezone.utc)
                dt_query["$lte"] = dt_to
            query["occurred_at"] = dt_query

        sort_spec = list(sort or [("occurred_at", DESCENDING), ("_id", DESCENDING)])
        try:
            total = self._col.count_documents(query)
            cursor = (
                self._col.find(query)
                .sort(sort_spec)
                .skip(skip)
                .limit(limit)
            )

            items: list[EventOut] = []
            for doc in cursor:
                # Convert Mongo _id -> id (str)
                event_dict = {**doc}
                event_dict["id"] = str(event_dict.pop("_id"))
                # Validate output date with pydantic
                items.append(EventOut(**event_dict))

            return PaginatedEvents(
                items=items,
                total=total,
                limit=limit,
                skip=skip,
                has_more=(skip + len(items) < total),
            )
        except PyMongoError as err:
            LOG.exception("Error listing audit events", extra={"error": err, "query": query})
            raise
