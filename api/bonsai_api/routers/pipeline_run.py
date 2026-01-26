"""Routes for managing pipeline runs."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Security, status

from bonsai_api.services.sample_service import add_pipeline_run_service
from bonsai_api.exceptions import ConflictError, DatabaseOperationError, EntryNotFound
from bonsai_api.db import Database
from bonsai_api.models.user import UserOutputDatabase
from bonsai_api.dependencies import get_current_active_user, get_database
from bonsai_api.models.pipeline import PipelineRun

LOG = logging.getLogger(__name__)
router = APIRouter()

READ_PERMISSION = "samples:read"
WRITE_PERMISSION = "samples:write"
UPDATE_PERMISSION = "samples:update"


@router.post("/pipeline-runs")
async def add_pipeline_run(
    body: PipelineRun,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Add a pipeline analysis run to a existing sample."""
    try:
        return await add_pipeline_run_service(db, pipeline=body)
    except DatabaseOperationError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
