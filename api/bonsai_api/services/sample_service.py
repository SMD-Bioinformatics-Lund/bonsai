"""Service layer for creating and modifying sample info."""

import logging
import uuid_utils as uuid
from pymongo.client_session import ClientSession
from pymongo.errors import DuplicateKeyError, PyMongoError
from pydantic import ValidationError
from bonsai_api.models.pipeline import PipelineRun
from bonsai_api.models.memberships import MembershipEdge
from bonsai_api.services.membership_service import add_memberships
from bonsai_api.crud.sample import get_sample_by_id, insert_sample_document, add_pipeline_run, pipeline_run_exists_for_sample, sample_exists, add_ska_index, add_sourmash_sketch
from bonsai_api.exceptions import ConflictError, DatabaseOperationError, EntryNotFound
from bonsai_api.models.sample import SampleInfoCreate, SampleRecordDb, SampleRecordOut
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.crud.utils import audit_event_context
from bonsai_api.db import Database
from api_client.audit_log.client import AuditLogClient
from api_client.audit_log.models import SourceType, Subject
from bonsai_api.crud.group import check_groups_exists

from bonsai_api.redis.minhash import (
    schedule_add_genome_signature,
    schedule_add_genome_signature_to_index,
)

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


async def add_pipeline_run_service(db: Database, *, sample_id: str, pipeline: PipelineRun, session: ClientSession | None = None) -> None:
    """Add a pipeline run to an existing sample.

    Raises EntryNotFound if sample missing and ConflictError if a pipeline run already
    exists for the sample.
    """
    if not sample_exists(db, sample_id=sample_id, session=session):
        LOG.error("Sample %s not found when adding pipeline run", sample_id)
        raise EntryNotFound(sample_id)
    
    if await pipeline_run_exists_for_sample(
        db, sample_id=sample_id,
        pipeline_run_id=pipeline.pipeline_run_id,
        session=session):
        raise ConflictError(f"Pipeline run already exists for sample. pipeline_run_id={pipeline.pipeline_run_id}")

    try:
        update_obj = await add_pipeline_run(db, sample_id=sample_id, doc=pipeline.model_dump(exclude_none=True), session=session)

        # Ensure update actually modified the document
        if update_obj.modified_count != 1:
            raise DatabaseOperationError(f"Failed to add pipeline run for {sample_id}")
    except Exception as exc:  # pragma: no cover - defensive
        LOG.exception("Unexpected error while adding pipeline run: %s", exc)
        raise DatabaseOperationError(str(exc)) from exc


async def get_sample_service(db: Database, *, sample_id: str, session: ClientSession | None = None) -> SampleRecordOut:
    """Retrieve a sample by its sample id."""
    raw_sample = await get_sample_by_id(db, sample_id=sample_id, session=session)
    
    if raw_sample is None:
        raise EntryNotFound(f"Sample with id '{sample_id}' not found")
    try:
        # get last pipeline run if set
        last_pipeline_run = None
        if (run_id := raw_sample.get("last_pipeline_run_id")) is not None:
            for pr in raw_sample.get("pipeline_runs", []):
                if pr.get("pipeline_run_id") == run_id:
                    last_pipeline_run = pr
                    break
        
        # merge analysis result and curations into dedicated field for API output
        return SampleRecordOut.model_validate({**raw_sample, "pipeline": last_pipeline_run})
    except ValidationError as ve:
        LOG.error("Validation error when retrieving sample %s: %s", sample_id, str(ve))
        raise DatabaseOperationError(
            f"Data integrity error when retrieving sample {sample_id}: {str(ve)}"
        ) from ve


async def add_ska_index_service(db: Database, *, sample_id: str, index_uri: str, session: ClientSession | None = None, force: bool = False):
    """Add a SKA index to a sample."""

    sample = await get_sample_service(db=db, sample_id=sample_id, session=session)

    # check if index has already been added
    if sample.ska_index is not None and not force:
        raise ConflictError("Sample {sample_id} is already associated with an index.")
    
    try:
        update_obj = await add_ska_index(db, sample_id=sample_id, index_uri=index_uri, session=session)

        # Ensure update actually modified the document
        if update_obj.modified_count != 1:
            raise DatabaseOperationError(f"Failed to add SKA index to {sample_id}")
    except Exception as exc:  # pragma: no cover - defensive
        LOG.exception("Unexpected error while adding SKA index: %s", exc)
        raise DatabaseOperationError(str(exc)) from exc


async def add_sourmash_index_service(db: Database, *, sample_id: str, sketch: str, session: ClientSession | None = None) -> dict[str, str]:
    """Add sourmash index to the database and schedule an addition job."""

    # check that sample exist
    sample = await get_sample_service(db, sample_id=sample_id, session=session)

    if sample.sourmash_sketch is not None:
        raise ConflictError("Sample {sample_id} is associated with index")

    # Schedule adding sketch and reindex
    add_sig_job = schedule_add_genome_signature(sample_id, sketch)
    index_job = schedule_add_genome_signature_to_index(
        [sample_id],
        depends_on=[add_sig_job.id],
    )

    # Add job id to sample
    add_idx_job = add_sig_job.id
    add_sourmash_sketch(db, sample_id=sample_id, sketch=add_idx_job, session=session)

    return {
        "add_sketch_job": add_idx_job,
        "index_job": index_job.id
    }