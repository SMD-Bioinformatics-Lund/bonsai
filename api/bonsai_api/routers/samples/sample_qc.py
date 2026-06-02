"""Quality control and analysis operations for samples."""

import logging

from api_client.audit_log.client import AuditLogClient
from bonsai_api.crud.sample import update_sample_qc_classification
from bonsai_api.db import Database
from bonsai_api.dependencies import (
    get_audit_log,
    get_current_active_user,
    get_database,
    get_request_context,
)
from bonsai_api.exceptions import DatabaseOperationError
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.pipeline import PipelineRun
from bonsai_api.models.qc import QcClassification
from bonsai_api.models.user import UserOutputDatabase
from bonsai_api.redis.minhash import (
    exclude_from_analysis,
    include_in_analysis,
    schedule_add_genome_signature_to_index,
    schedule_remove_genome_signature_from_index,
)
from bonsai_api.services.sample_service import (
    add_pipeline_run_service,
    get_sample_service,
)
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Security,
    status,
)

LOG = logging.getLogger(__name__)
router = APIRouter()

from .permissions import UPDATE_PERMISSION, WRITE_PERMISSION


def action_from_qc_classification(classification: QcClassification) -> str:
    """Determine action based on QC classification."""
    include_statuses = ["pass", "acceptable"]
    return "include" if str(classification).lower() in include_statuses else "exclude"


@router.post(
    "/samples/{sample_id}/pipeline-runs",
)
async def add_pipeline_run(
    sample_id: str,
    body: PipelineRun,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Add a pipeline analysis run to a existing sample."""
    try:
        return await add_pipeline_run_service(db, sample_id=sample_id, pipeline=body)
    except DatabaseOperationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@router.put(
    "/samples/{sample_id}/qc_status",
    response_model=QcClassification,
)
async def update_qc_status(
    classification: QcClassification,
    sample_id: str = Path(...),
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> bool:
    """Update sample QC status."""

    # dont update if the status dont change
    sample = await get_sample_service(db, sample_id=sample_id)
    if sample.qc_status == classification:
        return True

    # update
    status_obj: bool = await update_sample_qc_classification(
        db, sample_id, classification, ctx=req_ctx, audit=audit_log
    )

    # update if status should be excluded from indexing
    action = action_from_qc_classification(classification)
    if action == "include":
        include_job = include_in_analysis(sample_id)
        schedule_add_genome_signature_to_index(
            [sample_id],
            depends_on=[include_job.id],
        )
    else:
        # run exclude job and then remove signature from index
        exclude_job = exclude_from_analysis(sample_id)
        schedule_remove_genome_signature_from_index(
            [sample_id],
            depends_on=[exclude_job.id],
        )
    return status_obj
