"""Genome resource service layer."""

import logging
from pydantic import ValidationError
from pymongo.errors import PyMongoError
from fastapi import Request
from pathlib import Path

from api_client.audit_log.client import AuditLogClient
from api_client.audit_log.models import SourceType, Subject
from bonsai_api.crud.genomic_resource import (
    insert_genomic_resource,
    sample_has_resource,
    get_genomic_resource_by_id,
    list_genomic_resources_by_sample_id,
    delete_genomic_resource,
)
from bonsai_api.crud.sample import sample_exists
from bonsai_api.crud.utils import audit_event_context, managed_transaction
from bonsai_api.db import Database
from bonsai_api.exceptions import ConflictError, DatabaseOperationError, EntryNotFound
from bonsai_api.models.enums import FileSources
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.genomic_resource import (
    GenomicResourceCreate,
    GenomicResourceDb,
    GenomicResourceResponse,
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
) -> list[GenomicResourceResponse]:
    """Create a genomic resource set for a sample."""
    if not await sample_exists(db, sample_id=sample_id):
        raise EntryNotFound(f"Sample with ID {sample_id} not found")
    
    if resource.pipeline_run_id is None:
        raise ValueError("Resource dont have a pipeline run id!")

    has_resource_for_pipeline = await sample_has_resource(
        db, pipeline_id=resource.pipeline_run_id
    )
    if has_resource_for_pipeline and not force:
        raise ConflictError(
            f"Sample {sample_id} already has genomic resources for pipeline {resource.pipeline_run_id}. "
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
        base_dir = Path(settings.annotations_dir)

        payload = [
            GenomicResourceDb(
                format=r.format,
                type=r.type,
                name=r.name,
                path=to_relative_resource(r.path, base_dir=base_dir),
                index_path=to_relative_resource(r.index_path, base_dir=base_dir) if r.index_path else None,
                pipeline_id=resource.pipeline_run_id,
                reference_genome_id=resource.reference_genome_id,
                visibility=resource.visibility,
            ) for r in resource.resource_data
        ]
    except ValidationError as ve:
        LOG.error("Validation error while creating group: %s", str(ve))
        raise ValueError(f"Invalid data provided for creating group: {str(ve)}") from ve

    event_subject = Subject(id=sample_id, type=SourceType.USR)
    with audit_event_context(audit, "add_genomic_resource", ctx, event_subject):
        try:
            await insert_genomic_resource(
                db,
                sample_id=sample_id,
                resource_data=[p.model_dump(mode="json") for p in payload],
            )
            output_resources = [
                GenomicResourceResponse(
                    **p.model_dump(mode="json"),
                    url=resolve_resource_url(request, FileSources.GENOMIC_RESOURCES, p.path),
                    index_url=resolve_resource_url(request, FileSources.GENOMIC_RESOURCES, p.index_path) if p.index_path else None,
                ) for p in payload
            ]
        except PyMongoError as pme:
            LOG.error("MongoDB error while creating group: %s", str(pme))
            raise DatabaseOperationError(
                f"Database error inserting a new genomic resource: {str(pme)}"
            ) from pme

    return output_resources


async def get_genomic_resource_service(
    db: Database,
    *,
    resource_id: str,
    request: Request,
) -> GenomicResourceResponse:
    """Get a genomic resource."""
    resource = await get_genomic_resource_by_id(db, resource_id=resource_id)
    if not resource:
        raise EntryNotFound(f"Genomic resource with ID {resource_id} not found")

    try:
        return GenomicResourceResponse(
            id=resource_id,
            format=resource["format"],
            type=resource["type"],
            name=resource["name"],
            url=resolve_resource_url(request, FileSources.GENOMIC_RESOURCES, resource["path"]),
            index_url=resolve_resource_url(request, FileSources.GENOMIC_RESOURCES, resource["index_path"]) if resource.get("index_path") else None,
            pipeline_run_id=resource.get("pipeline_id"),
            reference_genome_id=resource["reference_genome_id"],
            visibility=resource["visibility"],
        )
    except ValidationError as ve:
        LOG.error("Validation error while parsing genomic resource: %s", str(ve))
        raise ValueError(
            f"Invalid data format for genomic resource with ID {resource_id}: {str(ve)}"
        ) from ve


async def list_genomic_resources_for_sample_service(
    db: Database,
    *,
    sample_id: str,
    request: Request,
) -> list[GenomicResourceResponse]:
    """List a genomic resources."""
    if not await sample_exists(db, sample_id=sample_id):
        raise EntryNotFound(f"Sample with ID {sample_id} not found")

    resources = await list_genomic_resources_by_sample_id(db, sample_id=sample_id)
    try:
        return [
            GenomicResourceResponse(
                id=r["id"],
                format=r["format"],
                type=r["type"],
                name=r["name"],
                url=resolve_resource_url(request, FileSources.GENOMIC_RESOURCES, r["path"]),
                index_url=resolve_resource_url(request, FileSources.GENOMIC_RESOURCES, r["index_path"]) if r.get("index_path") else None,
                pipeline_run_id=r.get("pipeline_id"),
                reference_genome_id=r["reference_genome_id"],
                visibility=r["visibility"],
            )
            for r in resources]
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
