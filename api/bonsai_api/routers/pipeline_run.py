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

# READ_PERMISSION = "pipeline:read"
# WRITE_PERMISSION = "pipeline:write"
# UPDATE_PERMISSION = "pipeline:update"
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
        await add_pipeline_run_service(db, pipeline=body)
    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except EntryNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DatabaseOperationError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
