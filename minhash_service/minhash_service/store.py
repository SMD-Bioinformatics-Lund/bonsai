"""Storage of minhash signatures."""

import logging
from typing import Iterable, Iterator

from bson import ObjectId
from pymongo import ASCENDING
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from .minhash.models import SignatureRecord  # Pydantic v2 model

LOG = logging.getLogger(__name__)


class SignatureStore:
    """
    Repository for signature CRUD.

    Connection lifetime is managed outside of this class.
    Pass in a ready Collection (with auth, TLS, timeouts, etc. configured).
    """

    def __init__(self, collection: Collection):
        self._col = collection

    # ---- schema management --------------------------------------------------
    def ensure_indexes(self) -> None:
        """Create indexes if they don't exist."""
        # Unique sample_id ensures deduplication
        self._col.create_index([("sample_id", ASCENDING)], name="ux_sample_id", unique=True)
        # Query accelerator for unindexed signatures
        self._col.create_index([("has_been_indexed", ASCENDING)], name="ix_has_been_indexed")

    # ---- create -------------------------------------------------------------
    def add_signature(self, signature: SignatureRecord) -> ObjectId | None:
        """
        Insert a signature. Returns the inserted ObjectId on success, None otherwise.
        """
        try:
            doc = signature.model_dump(by_alias=True, exclude_none=True)
            result = self._col.insert_one(doc)
            LOG.info("Signature added with id: %s", result.inserted_id)
            return result.inserted_id
        except DuplicateKeyError as _:
            LOG.warning("Duplicate signature for sample_id=%s", getattr(signature, "sample_id", None))
            return None
        except PyMongoError:
            LOG.exception("Error adding signature")
            raise  # Let caller decide how to handle unexpected DB faults

    def add_many(self, signatures: Iterable[SignatureRecord]) -> list[ObjectId]:
        """Bulk insert. Skips duplicates; raises on unexpected DB errors."""
        docs = [s.model_dump(by_alias=True, exclude_none=True) for s in signatures]
        try:
            result = self._col.insert_many(docs, ordered=False)
            return list(result.inserted_ids)
        except PyMongoError:
            LOG.exception("Bulk insert failed")
            raise

    # ---- read ---------------------------------------------------------------
    def get_by_sample_id(self, sample_id: str) -> SignatureRecord | None:
        """Get a signature by sample_id. Returns None if not found."""

        doc = self._col.find_one({"sample_id": sample_id})
        if not doc:
            return None
        # Option A: drop _id to avoid ObjectId in validation
        doc.pop("_id", None)
        return SignatureRecord.model_validate(doc)

    def get_signatures(
        self, *, limit: int | None = None, skip: int = 0
    ) -> Iterator[SignatureRecord]:
        """Get all signatures, optionally paginated."""
        cursor = self._col.find({}, projection={"_id": 0}).skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        for doc in cursor:
            yield SignatureRecord.model_validate(doc)

    def get_unindexed_signatures(
        self, *, limit: int | None = None
    ) -> Iterator[SignatureRecord]:
        """Get signatures that have not been indexed yet."""
        cursor = self._col.find({"has_been_indexed": False}, projection={"_id": 0})
        if limit:
            cursor = cursor.limit(limit)
        for doc in cursor:
            yield SignatureRecord.model_validate(doc)

    # ---- update -------------------------------------------------------------
    def mark_indexed(self, sample_id: str) -> bool:
        """Mark a signature as indexed. Returns True if a document was modified."""
        res = self._col.update_one(
            {"sample_id": sample_id, "has_been_indexed": False},
            {"$set": {"has_been_indexed": True}},
        )
        return res.modified_count > 0

    # ---- delete -------------------------------------------------------------
    def remove_by_sample_id(self, sample_id: str) -> int:
        """Delete by sample_id. Returns number of docs deleted."""
        res = self._col.delete_one({"sample_id": sample_id})
        if res.deleted_count == 0:
            LOG.info("No signature found with sample_id=%s", sample_id)
        return res.deleted_count
