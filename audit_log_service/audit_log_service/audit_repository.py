"""Audit log repository."""

import logging
from typing import Any
from bson import ObjectId
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

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
