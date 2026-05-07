"""Routes for adding new pipeline runs and ananlysis results to the database."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, Form, status, Body
from fastapi.responses import JSONResponse

from bonsai_api.models.analysis import CurationCreateRecord, CurationRecord, CurationCreateRecord
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.services.curation_service import approve_curation_service, create_curation_service, delete_curation_service, get_curations_service
from bonsai_api.services.analysis_service import ingest_analysis_service
from bonsai_api.db import Database
from bonsai_api.models.user import UserOutputDatabase
from bonsai_api.dependencies import (
    get_current_active_user,
    get_database,
    get_request_context,
    get_audit_log,
)
from api_client.audit_log.client import AuditLogClient
from .shared import RouterTags

LOG = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=[RouterTags.ANALYSIS])

READ_PERMISSION = "samples:read"
WRITE_PERMISSION = "samples:write"
UPDATE_PERMISSION = "samples:update"


@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_analysis(
    sample_id: str = Form(...),
    software: str = Form(...),
    software_version: str | None = Form(None),
    pipeline_run_id: str | None = Form(None),
    force: bool = Form(False, description="Overwrite existing analysis if present"),
    file: UploadFile = File(...),
    db: Database = Depends(get_database),
    user: UserOutputDatabase = Depends(get_current_active_user),
    ctx: ApiRequestContext=Depends(get_request_context),
    audit: AuditLogClient=Depends(get_audit_log),
):
    """Upload a software analysis file for a sample."""
    software_version = software_version or "0.0.1"
    data = await ingest_analysis_service(
        db,
        sample_id=sample_id,
        pipeline_run=pipeline_run_id,
        software=software,
        software_version=software_version,
        force=force,
        file=file,
        ctx=ctx,
        audit=audit,
    )

    return JSONResponse(status_code=201, content=data)


@router.post(
    "/{analysis_id}/curations",
    status_code=status.HTTP_201_CREATED,
    response_model=dict[str, str]
)
async def create_analysis_curation(
    analysis_id: str,
    curation: CurationCreateRecord,
    analysis_type: str = Body(description="Type of analysis result this curation applies to (e.g., 'resistance_variants')"),
    db: Database = Depends(get_database),
    user: UserOutputDatabase = Depends(get_current_active_user),
    ctx: ApiRequestContext = Depends(get_request_context),
    audit: AuditLogClient = Depends(get_audit_log),
):
    """Create a curation for an analysis result."""

    curation_id = await create_curation_service(
        db, analysis_id=analysis_id, analysis_type=analysis_type,
        curation=curation, curated_by=user.username, ctx=ctx, audit=audit
    )
    return {"curation_id": curation_id}


@router.get(
    "/{analysis_id}/curations",
    response_model=list[CurationRecord],
)
async def list_curations(
    analysis_id: str,
    analysis_type: str | None = Query(None, description="Filter by type"),
    decision: str | None = Query(None, description="Filter by decision"),
    approved_only: bool = Query(
        False, description="If true, only return approved curations"
    ),
    db: Database = Depends(get_database),
    user: UserOutputDatabase = Depends(get_current_active_user),
):
    """List all curations for an analysis."""
    filters = {"analysis_id": analysis_id}
    if analysis_type:
        filters["analysis_type"] = analysis_type
    if decision:
        filters["decision"] = decision
    if approved_only:
        filters["approved_by"] = True

    curations = await get_curations_service(db, filters=filters)
    return curations


@router.get(
    "/curations/{curation_id}",
    response_model=CurationRecord,
)
async def get_curation(
    curation_id: str,
    db: Database = Depends(get_database),
    user: UserOutputDatabase = Depends(get_current_active_user),
):
    """Get a specific curation record for a analysis."""
    curations = await get_curations_service(
        db, filters={"id": curation_id}
    )
    if not curations:
        raise HTTPException(status_code=404, detail="Curation not found")
    return curations[0]


@router.patch("/curations/{curation_id}/approve")
async def approve_curation(
    curation_id: str,
    db: Database = Depends(get_database),
    user: UserOutputDatabase = Depends(get_current_active_user),
    ctx: ApiRequestContext = Depends(get_request_context),
    audit: AuditLogClient = Depends(get_audit_log),
):
    """Approve a curation (second opinion)."""
    await approve_curation_service(
        db,
        curation_id=curation_id,
        approved_by=user.username,
        ctx=ctx,
        audit=audit,
    )


@router.delete(
    "/curations/{curation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_curation(
    curation_id: str,
    db: Database = Depends(get_database),
    user: UserOutputDatabase = Depends(get_current_active_user),
    ctx: ApiRequestContext = Depends(get_request_context),
    audit: AuditLogClient = Depends(get_audit_log),
):
    """Delete a curation."""
    await delete_curation_service(
        db,
        curation_id=curation_id,
        deleted_by=user.username,
        ctx=ctx,
        audit=audit,
    )
