"""Factory functions related to data stores and repos."""

from minhash_service.audit import AuditTrailRepository
from minhash_service.db import MongoDB
from minhash_service.minhash_service.signatures.repository import SignatureRepository
from minhash_service.integrity.report_repository import IntegrityReportRepository


def create_signature_repo() -> SignatureRepository:
    """Get signature repository."""
    collection = MongoDB.get_db().get_collection("signatures")
    repo = SignatureRepository(collection=collection)
    return repo


def create_audit_trail_repo() -> AuditTrailRepository:
    """Get audit trail store."""
    collection = MongoDB.get_db().get_collection("audit_trail")
    repo = AuditTrailRepository(collection=collection)
    return repo


def create_report_repo() -> IntegrityReportRepository:
    """Get integrity report store."""

    collection = MongoDB.get_db().get_collection("reports")
    repo = IntegrityReportRepository(collection=collection)
    return repo


def initialize_indexes():
    """Create indexes if they are missing."""
    create_signature_repo().ensure_indexes()
