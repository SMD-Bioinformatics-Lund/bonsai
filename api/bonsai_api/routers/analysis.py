"""Routes for adding new pipeline runs and ananlysis results to the database."""

import logging

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse

from bonsai_api.services.sample_service import add_pipeline_run_service
from bonsai_api.services.analysis_service import ingest_analysis_service
from bonsai_api.exceptions import ConflictError, DatabaseOperationError, EntryNotFound
from bonsai_api.db import Database
from bonsai_api.models.user import UserOutputDatabase
from bonsai_api.dependencies import (
    get_current_active_user,
    get_database,
    get_request_context,
    get_audit_log,
)
from bonsai_api.models.pipeline import PipelineRun

LOG = logging.getLogger(__name__)
router = APIRouter()

READ_PERMISSION = "samples:read"
WRITE_PERMISSION = "samples:write"
UPDATE_PERMISSION = "samples:update"


@router.post("/analyses")
async def upload_analysis(
    sample_id: str = Form(...),
    software: str = Form(...),
    software_version: str | None = Form(None),
    analysis_type: str = Form(...),
    file: UploadFile = File(...),
    db: Database = Depends(get_database),
    user: UserOutputDatabase = Depends(get_current_active_user),
    ctx=Depends(get_request_context),
    audit=Depends(get_audit_log),
):
    """Upload a software analysis file for a sample."""
    try:
        inserted_id = await ingest_analysis_service(
            db,
            sample_id=sample_id,
            analysis_type=analysis_type,
            software=software,
            software_version=software_version,
            file=file,
            ctx=ctx,
            audit=audit,
        )
    except EntryNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        LOG.exception("Error ingesting analysis for %s: %s", sample_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return JSONResponse(status_code=201, content={"analysis_id": inserted_id})