"""Storage of minhash signatures."""

import logging
from typing import Any, Iterable, Iterator


from bson import ObjectId
from pymongo import ASCENDING
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from ..minhash.models import SignatureRecord

LOG = logging.getLogger(__name__)


class SignatureRepository:
    """
    Repository for signature CRUD.

    Connection lifetime is managed outside of this class.
    Pass in a ready Collection (with auth, TLS, timeouts, etc. configured).
    """

    def __init__(self, collection: Collection[Any]):
        self._col = collection

    # ---- schema management --------------------------------------------------
    def ensure_indexes(self) -> None:
        """Create indexes if they don't exist."""
        # Unique sample_id ensures deduplication
        self._col.create_index(
            [("sample_id", ASCENDING)], name="ux_sample_id", unique=True
        )
        # Query accelerator for unindexed signatures
        self._col.create_index(
            [("has_been_indexed", ASCENDING)], name="ix_has_been_indexed"
        )

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
            LOG.warning(
                "Duplicate signature for sample_id=%s",
                getattr(signature, "sample_id", None),
            )
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

        doc = self._col.find_one({"sample_id": sample_id}, projection={"_id": 0})
        if not doc:
            return None
        return SignatureRecord.model_validate(doc)
    
    def get_all_signatures(self) -> Iterator[SignatureRecord]:
        """Get all signatures in the database."""
        cursor = self._col.find(projection={"_id": 0})
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

    def count_by_checksum(self, checksum: str) -> int:
        """Count signatures by checksum. Returns 0 if none found."""
        return self._col.count_documents({"checksum": checksum})

    # ---- update -------------------------------------------------------------
    def _set_flag(self, sample_id: str, status: bool, flag: str) -> bool:

        """
        Set flags, such as 'has_been_indexed', to the desired state.
        Returns True if a document was modified (i.e., state actually changed).
        """
        res = self._col.update_one(
            {"sample_id": sample_id, flag: {"$ne": status}},
            {"$set": {flag: status}},

        )
        return res.modified_count > 0

    def mark_indexed(self, sample_id: str) -> bool:
        """Mark a signature as indexed. Returns True if a document was modified."""
        return self._set_flag(sample_id, flag="has_been_indexed", status=True)

    def unmark_indexed(self, sample_id: str) -> bool:
        """Mark a signature as not indexed. Returns True if a document was modified."""
        return self._set_flag(sample_id, flag="has_been_indexed", status=False)

    def exclude_from_analysis(self, sample_id: str) -> bool:
        """Exclude a sample from future analysis. Returns True if a document was modified."""
        return self._set_flag(sample_id, flag="exclude_from_analysis", status=False)

    def marked_for_deletion(self, sample_id: str) -> bool:
        """Mark a signature for deletion. Returns True if a document was modified."""
        return self._set_flag(sample_id, flag="mark_for_deletion", status=False)

    # ---- delete -------------------------------------------------------------
    def remove_by_sample_id(self, sample_id: str) -> int:
        """Delete by sample_id. Returns number of docs deleted."""
        res = self._col.delete_one({"sample_id": sample_id})
        if res.deleted_count == 0:
            LOG.info("No signature found with sample_id=%s", sample_id)
        return res.deleted_count
