"""Service functions for managing curation records."""

import logging

from typing import Any
from pydantic import ValidationError, TypeAdapter
from pymongo import UpdateOne
from pymongo.client_session import ClientSession

from api.bonsai_api.utils import get_timestamp
from bonsai_api.crud.curation import create_curation, delete_curation_crud, get_curation_by_id_crud, get_curations_crud, update_curation_crud
from bonsai_api.exceptions import DatabaseOperationError, EntryNotFound
from bonsai_api.crud.utils import managed_transaction
from bonsai_api.crud.analysis import get_analysis
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.analysis import AnalysisResult, CurationRecord, CurationCreateRecord
from bonsai_api.db import Database
from api_client.audit_log.models import Subject, SourceType
from api_client.audit_log import AuditLogClient, EventCreate


LOG = logging.getLogger(__name__)


async def create_curation_service(
        db: Database,
        *,
        analysis_id: str,
        analysis_type: str,
        curation: CurationCreateRecord,
        curated_by: str,
        ctx: ApiRequestContext,
        audit: AuditLogClient | None = None,
    ) -> str:
    """Retrieve curations for an analysis."""
    async with managed_transaction(db.client) as txn:
        # Verify that analysis exists
        analysis = await get_analysis(db, analysis_id=analysis_id, session=txn)
        if not analysis:
            raise EntryNotFound(f"Analysis with id '{analysis_id}' was not found")

        if analysis_type not in analysis.get('envelopes', {}):
            raise EntryNotFound(f"Analysis '{analysis_id}' dont have result of type '{analysis_type}'")
        
        try:
            # Set analysis id on curation record and validate curation record
            curation_data = curation.model_dump()
            curation_data.update({"analysis_id": analysis_id, "analysis_type": analysis_type, "curated_by": curated_by})
            record = TypeAdapter(CurationRecord).validate_python(curation_data)

            # insert into database
            curation_id = await create_curation(db, doc=record.model_dump(exclude_none=True), session=txn)

            # Audit log
            if isinstance(audit, AuditLogClient):
                subject = Subject(id=analysis_id, type=SourceType.USR)
                event_data = {
                    "curation_id": curation_id,
                    "analysis_id": analysis_id,
                    "analysis_type": analysis_type,
                    "curation_type": curation.annotation_type,
                    "decision": curation.decision,
                }
                event = EventCreate(
                    source_service="bonsai_api",
                    event_type="create_curation",
                    actor=ctx.actor if ctx else None,
                    subject=subject,
                    metadata=event_data,
                )
                audit.post_event(event)

            LOG.info(
                "Created curation %s for analysis %s by %s",
                curation_id, analysis_id, curated_by
            )
            return curation_id
        except ValidationError as ve:
            LOG.error("Curation validation error: %s", ve)
            raise DatabaseOperationError(
                f"Curation validation error: {str(ve)}"
            ) from ve
        except Exception as exc:
            LOG.error("Error storing curation")
            raise DatabaseOperationError(str(exc)) from exc


async def get_curations_service(
        db: Database, *, filters: dict[str, Any] | None = None,
    ) -> list[CurationRecord]:
    """Retrieve curations for an analysis."""

    curations = await get_curations_crud(db, filters=filters or {})

    try:
        # Parse back to discriminated union
        adapter = TypeAdapter(CurationRecord)
        return [adapter.validate_python(c) for c in curations]
    except ValidationError as ve:
        LOG.error("Curation validation error: %s", ve)
        raise DatabaseOperationError(
            f"Curation validation error: {str(ve)}"
        ) from ve
    except Exception as exc:
        LOG.error("Error storing curation")
        raise DatabaseOperationError(str(exc)) from exc


async def approve_curation_service(
    db: Database, 
    *,
    curation_id: str,
    approved_by: str,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> None:
    """Approve a curation record."""

    # get existing curations
    curation = await get_curation_by_id_crud(db, curation_id=curation_id)
    if not curation:
        raise EntryNotFound(f"Curation {curation_id} not found")
    
    # uppdate approval
    await update_curation_crud(
        db, curation_id=curation_id, updates={"approved_by": approved_by}
    )
    # Audit log
    if isinstance(audit, AuditLogClient):
        subject = Subject(id=curation_id, type=SourceType.USR)
        event = EventCreate(
            source_service="bonsai_api",
            event_type="approve_curation",
            actor=ctx.actor if ctx else None,
            subject=subject,
            metadata={"approved_by": approved_by},
        )
        audit.post_event(event)


async def delete_curation_service(
    db: Database,
    *,
    curation_id: str,
    deleted_by: str,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> None:
    """Delete a curation record."""
    curation = await get_curation_by_id_crud(db, curation_id=curation_id)
    if not curation:
        raise EntryNotFound(f"Curation {curation_id} not found")
    
    await delete_curation_crud(db, curation_id=curation_id)
    
    # Audit log
    if isinstance(audit, AuditLogClient):
        subject = Subject(id=curation_id, type=SourceType.USR)
        event = EventCreate(
            source_service="bonsai_api",
            event_type="delete_curation",
            actor=ctx.actor if ctx else None,
            subject=subject,
            metadata={"deleted_by": deleted_by},
        )
        audit.post_event(event)
    
    LOG.info("Deleted curation %s", curation_id)


async def sync_curation_sumary_for_analysis(
    db: Database,
    *,
    sample_id: str,
    analysis_id: str,
    analysis: AnalysisResult,
    session: ClientSession | None = None
):
    """Re-sync the the curration summary for one analysis result."""
    # Fetch all curations for this analysis from canonical collection
    curations = await get_curations_crud(
        db,
        filters={"analysis_id": analysis_id},
        session=session
    )

    # Pull old curation recrods
    ops: list[UpdateOne] = []
    for atype in analysis.envelopes:
        ops.append(
            UpdateOne(
                {"sample_id": sample_id},
                {
                    "$pull": {
                        "curations": {
                            "software": analysis.software,
                            "analysis_type": atype
                        }
                    }
                }
            )
        )

    # add updated curation to sample object
    ops.append(
        UpdateOne(
            {"sample_id": sample_id},
            {
                "$push": { "curations": curations },
                "$set": { "modified_at": get_timestamp() },
            }
        )
    )
    result = await db.sample_collection.bulk_write(ops, ordered=False, session=session)
    return result.modified_count == 1