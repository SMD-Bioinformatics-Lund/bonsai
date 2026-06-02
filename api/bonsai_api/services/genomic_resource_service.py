"""Genome resource service layer."""

import logging
from pydantic import ValidationError
from pymongo.errors import PyMongoError
from fastapi import Request

from api_client.audit_log.client import AuditLogClient
from api_client.audit_log.models import SourceType, Subject
from bonsai_api.crud.genomic_resource import (
    sample_has_resource,
    get_genomic_resources_by_id,
    delete_genomic_resource,
)
from bonsai_api.crud.sample import sample_exists
from bonsai_api.crud.utils import audit_event_context, managed_transaction
from bonsai_api.db import Database
from bonsai_api.exceptions import ConflictError, DatabaseOperationError, EntryNotFound
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.genomic_resource import (
    GenomicResourceCreate,
    GenomicResourceDb,
    GenomicResourceResponse,
    ResourceInput,
)
from bonsai_api.io import to_relative_resource
from bonsai_api.models.user import UserContext
from bonsai_api.config import settings

from .reference_genomes import get_reference_genome_service
from .utils import resolve_resource_url

LOG = logging.getLogger(__name__)


async def create_genomic_resource_service(
    db: Database,
    *,
    sample_id: str,
    request: Request,
    force: bool = False,
    resource: GenomicResourceCreate,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> GenomicResourceResponse:
    """Create a genomic resource set for a sample."""
    if not await sample_exists(db, sample_id=sample_id):
        raise EntryNotFound(f"Sample with ID {sample_id} not found")

    has_resource_for_pipeline = await sample_has_resource(
        db, sample_id=sample_id, pipeline_id=resource.pipeline_id
    )
    if has_resource_for_pipeline and not force:
        raise ConflictError(
            f"Sample {sample_id} already has genomic resources for pipeline {resource.pipeline_id}. "
            "Use force=True to overwrite."
        )
    
    try:
        # Validate reference genome exists
        await get_reference_genome_service(db, resource_id=resource.reference_genome_id, request=request)
    except EntryNotFound as exc:
        raise EntryNotFound(
            f"Reference genome with ID {resource.reference_genome_id} not found"
        ) from exc

    # Create payload
    try:
        base_dir = settings.annotations_dir

        payload = GenomicResourceDb(
            sample_id=sample_id,
            pipeline_id=resource.pipeline_id,
            resource_data=[
                ResourceInput(
                    format=r.format,
                    type=r.type,
                    name=r.name,
                    path=to_relative_resource(r.path, base_dir=base_dir),
                    index_path=to_relative_resource(r.index_path, base_dir=base_dir) if r.index_path else None,
                ) for r in resource.resource_data],
        )
    except ValidationError as ve:
        LOG.error("Validation error while creating group: %s", str(ve))
        raise ValueError(f"Invalid data provided for creating group: {str(ve)}") from ve
    event_subject = Subject(id=sample_id, type=SourceType.USR)
    with audit_event_context(audit, "add_genomic_resource", ctx, event_subject):
        try:
            await db.insert_genomic_resource(
                sample_id=sample_id,
                pipeline_id=resource.pipeline_id,
                resource_data=payload.model_dump(),
            )
            output_resource = GenomicResourceResponse(
                **payload.model_dump(mode="json"),
                url=resolve_resource_url(request, payload.resource_data[0].path),
            )
        except PyMongoError as pme:
            LOG.error("MongoDB error while creating group: %s", str(pme))
            raise DatabaseOperationError(
                f"Database error inserting a new genomic resource: {str(pme)}"
            ) from pme

    return output_resource


async def get_genomic_resource_service(
    db: Database,
    *,
    resource_id: str,
) -> GenomicResourceResponse:
    """Get a genomic resource."""
    resources = await get_genomic_resources_by_id(db, resource_id=resource_id)
    if not resources:
        raise EntryNotFound(f"Genomic resource with ID {resource_id} not found")

    if len(resources) > 1:
        LOG.warning(
            "Multiple genomic resources found with ID %s, returning the first one",
            resource_id,
        )
    
    try:
        return GenomicResourceResponse.model_validate(resources[0])
    except ValidationError as ve:
        LOG.error("Validation error while parsing genomic resource: %s", str(ve))
        raise ValueError(
            f"Invalid data format for genomic resource with ID {resource_id}: {str(ve)}"
        ) from ve


async def list_genomic_resources_for_sample_service(
    db: Database,
    *,
    sample_id: str,
) -> list[GenomicResourceResponse]:
    """List a genomic resources."""
    resources = await get_genomic_resources_by_id(db, sample_id=sample_id)
    try:
        return [GenomicResourceResponse.model_validate(resource) for resource in resources]
    except ValidationError as ve:
        LOG.error("Validation error while parsing genomic resource: %s", str(ve))
        raise ValueError(f"Invalid data format for genomic resource: {str(ve)}") from ve


async def delete_genomic_resource_service(
    db: Database,
    *,
    resource_id: str,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
    user: UserContext,
) -> dict[str, int]:
    """Delete a genomic resource."""

    event_subject = Subject(id=resource_id, type=SourceType.USR, attributes={"user_id": user.user_id})
    with audit_event_context(audit, "delete_genomic_resource", ctx, event_subject):
        async with managed_transaction(db.client) as sess:
            result = await delete_genomic_resource(
                db, resource_id=resource_id, session=sess
            )

            if result.matched_count == 0:
                raise EntryNotFound(f"Genomic resource with ID {resource_id} not found")

            if result.modified_count == 0:
                LOG.warning(
                    "Genomic resource with ID %s was found but not deleted", resource_id
                )
                raise DatabaseOperationError(
                    f"Failed to delete genomic resource with ID {resource_id}"
                )

    return {"deleted_count": result.modified_count}
