"""Service layer for creating and modifying sample info."""

import logging
from pymongo.client_session import ClientSession
from pymongo.errors import DuplicateKeyError, PyMongoError
from pydantic import ValidationError
from bonsai_api.models.memberships import MembershipEdge
from bonsai_api.services.membership_service import add_memberships
from bonsai_api.crud.sample import insert_sample_document
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
    payload = SampleRecordDb(
        sample_id=sample.sample_id,
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
        return resp.inserted_id
