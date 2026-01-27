"""Service layer for creating and modifying sample info."""

import logging
import uuid_utils as uuid
from pymongo.client_session import ClientSession
from pymongo.errors import DuplicateKeyError, PyMongoError
from pydantic import ValidationError
from bonsai_api.models.pipeline import PipelineRun
from bonsai_api.models.memberships import MembershipEdge
from bonsai_api.services.membership_service import add_memberships
from bonsai_api.crud.sample import insert_sample_document, add_pipeline_run, pipeline_run_exists_for_sample, sample_exists
from bonsai_api.exceptions import ConflictError, DatabaseOperationError, EntryNotFound
from bonsai_api.models.sample import SampleInfoCreate, SampleRecordDb
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.crud.utils import audit_event_context
from bonsai_api.db import Database
from api_client.api_client.audit_log.client import AuditLogClient
from api_client.audit_log.models import SourceType, Subject
from bonsai_api.crud.group import check_groups_exists

LOG = logging.getLogger(__name__)


async def create_sample_service(
    db: Database,
    *,
    sample: SampleInfoCreate,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
    session: ClientSession | None = None,
) -> str | None:
    """Create a new sample document in the database."""
    # verify that groups exists
    if len(sample.groups) > 0 and (missing_groups := check_groups_exists(db, group_ids=sample.groups)):
        raise EntryNotFound(
            "One or more groups are not in the database", 
            detail=missing_groups
        )
    
    # build sample payload
    internal_sample_id = str(uuid.uuid7())
    payload = SampleRecordDb(
        sample_id=internal_sample_id,
        external_sample_id=sample.sample_id,
        sample_name=sample.sample_name,
        lims_id=sample.lims_id,
        groups=sample.groups,
        owners=[ctx.actor.id] or sample.owners,  # default to user that uploaded sample
        owner_organizations=sample.owner_organizations,
        access_groups=sample.access_groups,
        visibility=sample.visibility,
        sequencing=sample.sequencing,
        metadata=sample.metadata
    )

    event_subject = Subject(id=sample.sample_id, type=SourceType.USR)
    with audit_event_context(audit, "create_sample", ctx, event_subject):
        try:
            # create sample object
            resp = await insert_sample_document(
                db, doc=payload.model_dump(exclude_none=True), session=session
            )
            # create memberships if needed
            if len(sample.groups) > 0:
                edges = [
                    MembershipEdge(sample_id=sample.sample_id, group_id=gr) 
                    for gr in sample.groups
                ]
                await add_memberships(db=db, edges=edges, session=session)
        except DuplicateKeyError as dke:
            LOG.error("Duplicate key error while creating group: %s", str(dke))
            raise ConflictError(
                f"Sample with id {sample.sample_id} already exists."
            ) from dke
        except PyMongoError as pme:
            LOG.error("MongoDB error while creating group: %s", str(pme))
            raise DatabaseOperationError(
                f"Database error occurred while creating group: {str(pme)}"
            ) from pme
        except ValidationError as ve:
            LOG.error("Validation error while creating group: %s", str(ve))
            raise ValueError(
                f"Invalid data provided for creating group: {str(ve)}"
            ) from ve
        return {
            "inserted_id": str(resp.inserted_id), 
            "internal_sample_id": internal_sample_id, 
            "external_sample_id": sample.sample_id
        }


async def add_pipeline_run_service(db: Database, *, pipeline: PipelineRun, session: ClientSession | None = None) -> None:
    """Add a pipeline run to an existing sample.

    Raises EntryNotFound if sample missing and ConflictError if a pipeline run already
    exists for the sample.
    """
    sample_id = pipeline.sample_id
    if not sample_exists(db, sample_id=pipeline.sample_id, session=session):
        LOG.error("Sample %s not found when adding pipeline run", sample_id)
        raise EntryNotFound(pipeline.sample_id)
    
    if await pipeline_run_exists_for_sample(
        db, sample_id=sample_id, 
        pipeline_run_id=pipeline.pipeline_run_id,
        session=session):
        raise ConflictError(f"Pipeline run already exists for sample. pipeline_run_id={pipeline.pipeline_run_id}")

    try:
        sample_id = pipeline.sample_id
        update_obj = await add_pipeline_run(db, sample_id=sample_id, doc=pipeline.model_dump(exclude_none=True), session=session)

        # Ensure update actually modified the document
        if update_obj.modified_count != 1:
            raise DatabaseOperationError(f"Failed to add pipeline run for {sample_id}")
    except Exception as exc:  # pragma: no cover - defensive
        LOG.exception("Unexpected error while adding pipeline run: %s", exc)
        raise DatabaseOperationError(str(exc)) from exc
