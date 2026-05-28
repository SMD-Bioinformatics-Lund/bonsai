"""Genome asset service layer."""

from bonsai_api.models.user import UserContext
from bonsai_api.db import Database
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.genome_asset import GenomicAssetCreate
from api_client.api_client.audit_log.client import AuditLogClient


def create_genomic_asset_service(
        db: Database,
        *,
        sample_id: str,
        asset: GenomicAssetCreate,
        ctx: ApiRequestContext,
        audit: AuditLogClient | None = None,
    ):
    """Create a genomic asset set for a sample."""


def list_genomic_asset_service(
        db: Database,
        *,
        sample_id: str,
        user: UserContext,
    ):
    """List a genomic assets."""


def delete_genomic_asset_service(
        db: Database,
        *,
        asset_id: str,
        ctx: ApiRequestContext,
        audit: AuditLogClient | None = None,
        user: UserContext,
    ):
    """Create a genomic asset set for a sample."""