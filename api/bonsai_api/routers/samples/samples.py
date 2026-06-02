"""Core sample CRUD operations."""

import logging

from bonsai_api.crud.utils import managed_transaction
from bonsai_api.crud.sample import get_samples_full
from bonsai_api.crud.summary import get_samples_summary
from bonsai_api.db import Database
from bonsai_api.dependencies import (
    get_audit_log,
    get_current_active_user,
    get_database,
    get_request_context,
)
from bonsai_api.exceptions import AuditLogError
from bonsai_api.models.base import MultipleRecordsResponseModel
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.sample import (
    SampleInfoCreate,
    SampleRecordDb,
    SampleRecordOut,
    InputSamplesSummary,
    UpdateSampleInputModel,
)
from bonsai_api.models.user import UserOutputDatabase
from bonsai_api.services.sample_service import (
    create_sample_service,
    delete_sample_service,
    get_sample_service,
)
from bonsai_api.crud.builder.summary_manifest import MANIFEST
from bonsai_api.crud.builder.types import ManifestOutput
from api_client.audit_log.client import AuditLogClient
from api_client.audit_log.models import EventCreate, SourceType, Subject
from api_client.core.exceptions import ApiRequestError
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Security,
    status,
)
from fastapi.responses import JSONResponse

from .permissions import READ_PERMISSION, UPDATE_PERMISSION, WRITE_PERMISSION

LOG = logging.getLogger(__name__)
router = APIRouter()

# Shared import constant
SAMPLE_ID_PATH = "sample_id"



@router.post("/samples/summary")
async def query_samples(
    body: InputSamplesSummary,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Get samples."""
    match = {}
    if body.group_id:
        match["groups"] = body.group_id
    if body.sid:
        match["sample_id"] = {"$in": body.sid}

    try:
        return await get_samples_summary(
            db,
            MANIFEST,
            match=match,
            fields=body.fields,
            sort=body.sort,
            limit=body.limit,
            offset=body.offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


@router.get("/samples/summary/manifest")
async def get_summary_manifest():
    """Get valid fields for the sample summary."""
    public = ManifestOutput.from_internals(MANIFEST)
    resp = JSONResponse(content=public.model_dump(exclude_none=True))
    resp.headers["ETag"] = public.etag
    return resp


@router.get("/samples", response_model=MultipleRecordsResponseModel)
async def list_samples(
    group_id: str | None = Query(None, description="Filter group by ID"),
    sid: list[str] | None = Query(
        None, description="Fileter by sample ids (Use POST for large sets)"
    ),
    fields: list[str] | None = Query(None, description="Fields to include in response"),
    sort: str = Query("-created_at"),
    limit: int = Query(50, ge=0),
    offset: int = Query(0, ge=0),
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Get samples from the database. It can return either the full or summarized sample information."""
    try:
        match = {}
        if group_id:
            match["groups"] = group_id
        if sid:
            match["sample_id"] = {"$in": sid}

        return await get_samples_full(
            db=db, match=match, fields=fields, sort=sort, limit=limit, offset=offset
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


@router.post("/samples/", status_code=status.HTTP_201_CREATED)
async def create_sample(
    sample: SampleInfoCreate,
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
) -> dict[str, str]:
    """Entrypoint for creating a new sample."""
    resp = await create_sample_service(db, sample=sample, ctx=req_ctx, audit=audit_log)
    return {"type": "success", **resp}


@router.delete("/samples/", status_code=status.HTTP_200_OK)
async def delete_many_samples(
    sample_ids: list[str],
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
):
    """Delete multiple samples from the database."""

    async with managed_transaction(db.client) as sess:
        removed = []
        jobs = []
        audit_events: list[EventCreate] = []

        for sample_id in sample_ids:
            job_status = await delete_sample_service(db, sample_id=sample_id, session=sess)
            if job_status:
                removed.append(sample_id)
                jobs.append(job_status['remove_sourmash'])

                if isinstance(audit_log, AuditLogClient):
                    event_subject = Subject(id=sample_id, type=SourceType.USR)
                    audit_events.append(
                        EventCreate(
                            source_service="bonsai_api",
                            event_type="delete_sample",
                            actor=req_ctx.actor,
                            subject=event_subject,
                            metadata=req_ctx.metadata,
                        )
                    )

        for event in audit_events:
            try:
                audit_log.post_event(event)
            except ApiRequestError as exc:
                raise AuditLogError(
                    f"Audit log event failed for sample {event.subject.id}: {exc}"
                ) from exc
    return {
        "sample_ids": sample_ids,
        "n_deleted": len(removed),
        "remove_signature_jobs": jobs,
    }


@router.get("/samples/{sample_id}", response_model_by_alias=False)
async def read_sample(
    sample_id: str = Path(...),
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
) -> SampleRecordOut:
    """Read sample with sample id from database."""
    return await get_sample_service(db, sample_id=sample_id)


@router.put("/samples/{sample_id}", response_model=SampleRecordDb)
async def update_sample(
    update_data: UpdateSampleInputModel,
    sample_id: str = Path(...),
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
):
    """Update sample with sample id from database.

    Take either a partial or full result as input.
    """
    return sample_id


@router.delete("/samples/{sample_id}", status_code=status.HTTP_200_OK)
async def delete_sample(
    sample_id: str = Path(...),
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
):
    """Delete the specific sample."""
    status_result = await delete_sample_service(db, sample_id=sample_id)
    if isinstance(audit_log, AuditLogClient) and status_result:
        event_subject = Subject(id=sample_id, type=SourceType.USR)
        event = EventCreate(
            source_service="bonsai_api",
            event_type="delete_sample",
            actor=req_ctx.actor,
            subject=event_subject,
            metadata=req_ctx.metadata,
        )
        try:
            audit_log.post_event(event)
        except ApiRequestError as exc:
            raise AuditLogError(
                f"Audit log event failed for sample {sample_id}: {exc}"
            ) from exc
    return status_result
