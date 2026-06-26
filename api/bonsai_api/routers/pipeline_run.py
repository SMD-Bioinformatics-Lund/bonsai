"""Routes for managing pipeline runs."""
import logging

from fastapi import APIRouter, Depends, Security

from bonsai_api.db import Database
from bonsai_api.models.user import UserOutputDatabase
from bonsai_api.dependencies import get_current_active_user, get_database

from .tags import RouterTags

LOG = logging.getLogger(__name__)
router = APIRouter(tags=[RouterTags.PIPELINE_RUNS])

READ_PERMISSION = "samples:read"
WRITE_PERMISSION = "samples:write"
UPDATE_PERMISSION = "samples:update"


@router.get("/pipeline-runs/{pipeline_run_id}/samples")
async def get_samples_from_pipeline_run(
    pipeline_run_id: str,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Get get samples analysed with a pipeline run."""
    return pipeline_run_id