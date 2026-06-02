"""Genome resource service layer."""

import logging
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from bonsai_api.crud.utils import audit_event_context
from bonsai_api.exceptions import DatabaseOperationError, EntryNotFound, ConflictError
from bonsai_api.models.user import UserContext
from bonsai_api.db import Database
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.genomic_resource import GenomicResourceCreate, GenomicResourceOut, GenomicResourceDb
from bonsai_api.crud.sample import sample_exists
from bonsai_api.crud.genomic_resource import sample_has_resource, get_genomic_resources_by_id
from api_client.audit_log.client import AuditLogClient
from api_client.audit_log.models import SourceType, Subject


LOG = logging.getLogger(__name__)


async def create_genomic_resource_service(
        db: Database,
        *,
        sample_id: str,
        force: bool = False,
        resource: GenomicResourceCreate,
        ctx: ApiRequestContext,
        audit: AuditLogClient | None = None,
    ) -> GenomicResourceOut:
    """Create a genomic resource set for a sample."""
    if not await sample_exists(db, sample_id=sample_id):
        raise EntryNotFound(f"Sample with ID {sample_id} not found")

    has_resource_for_pipeline = await sample_has_resource(db, sample_id=sample_id, pipeline_id=resource.pipeline_id)
    if has_resource_for_pipeline and not force:
        raise ConflictError(
            f"Sample {sample_id} already has genomic resources for pipeline {resource.pipeline_id}. "
            "Use force=True to overwrite."
        )
    
    # Create payload
    try:
        payload = GenomicResourceDb(
            sample_id=sample_id,
            pipeline_id=resource.pipeline_id,
            resource_data=resource.resource_data
        )
    except ValidationError as ve:
        LOG.error("Validation error while creating group: %s", str(ve))
        raise ValueError(
            f"Invalid data provided for creating group: {str(ve)}"
        ) from ve
    event_subject = Subject(id=sample_id, type=SourceType.USR)
    with audit_event_context(audit, "add_genomic_resource", ctx, event_subject):
        try:
            await db.insert_genomic_resource(sample_id=sample_id, pipeline_id=resource.pipeline_id, resource_data=payload.model_dump())
        except PyMongoError as pme:
            LOG.error("MongoDB error while creating group: %s", str(pme))
            raise DatabaseOperationError(
                f"Database error inserting a new genomic resource: {str(pme)}"
            ) from pme

    return GenomicResourceOut(**payload.model_dump())


async def get_genomic_resource_service(
        db: Database,
        *,
        resource_id: str,
    ) -> GenomicResourceOut:
    """Get a genomic resource."""
    resources = await get_genomic_resources_by_id(db, resource_id=resource_id)
    if not resources:
        raise EntryNotFound(f"Genomic resource with ID {resource_id} not found")


async def list_genomic_resources_for_sample_service(
        db: Database,
        *,
        sample_id: str,
        user: UserContext,
    ) -> list[GenomicResourceOut]:
    """List a genomic resources."""


async def delete_genomic_resource_service(
        db: Database,
        *,
        resource_id: str,
        ctx: ApiRequestContext,
        audit: AuditLogClient | None = None,
        user: UserContext,
    ):
    """Create a genomic resource set for a sample."""