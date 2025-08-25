"""Audit trail store."""

import logging

from bson import ObjectId
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from .minhash.models import Event

LOG = logging.getLogger(__name__)


class AuditTrailStore:
    """
    Store for audit trail entries.

    Connection lifetime is managed outside of this class.
    Pass in a ready Collection (with auth, TLS, timeouts, etc. configured).
    """

    def __init__(self, collection: Collection):
        self._col = collection

    def log_event(self, event: Event) -> ObjectId | None:
        """
        Insert an audit event. Returns the inserted ObjectId on success, None otherwise.
        """
        try:
            result = self._col.insert_one(event)
            LOG.info("Audit event logged with id: %s", result.inserted_id)
            return result.inserted_id
        except PyMongoError:
            LOG.exception("Error logging audit event")
            raise  # Let caller decide how to handle unexpected DB faults
