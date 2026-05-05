"""Service functions for managing curation records."""

from collections import defaultdict
import logging

from typing import Any
from pydantic import ValidationError, TypeAdapter
from pymongo import UpdateOne
from pymongo.client_session import ClientSession
from pymongo.errors import DuplicateKeyError

from bonsai_api.utils import get_timestamp
from bonsai_api.crud.curation import create_curation, delete_curation_crud, get_curation_by_id_crud, get_curations_crud, update_curation_crud
from bonsai_api.exceptions import ConflictError, DatabaseOperationError, EntryNotFound
from bonsai_api.crud.utils import managed_transaction
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.analysis import CurationRecord, CurationCreateRecord
from bonsai_api.db import Database
from api_client.audit_log.models import Subject, SourceType
from api_client.audit_log import AuditLogClient, EventCreate

from .analysis_service import group_for, get_analysis_service


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
        analysis = await get_analysis_service(db, analysis_id=analysis_id, session=txn)

        if analysis_type not in analysis.envelopes:
            raise EntryNotFound(f"Analysis '{analysis_id}' dont have result of type '{analysis_type}'")
        
        try:
            # Enrich curation with analysis context and validate
            curation_data = curation.model_dump()
            curation_data.update({
                "sample_id": analysis.sample_id,
                "analysis_id": analysis_id,
                "analysis_type": analysis_type,
                "curated_by": curated_by,
            })
            record = TypeAdapter(CurationRecord).validate_python(curation_data)

            # insert into database
            curation_id = record.id
            await create_curation(db, doc=record.model_dump(exclude_none=True), session=txn)

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

            # sync data to sample object after update
            await sync_curation_summary_for_analysis(
                db, sample_id=curation_data['sample_id'], analysis_id=analysis_id, session=txn
            )
            return curation_id
        except DuplicateKeyError as dke:
            LOG.error("Duplicate key error while creating group: %s", str(dke))
            raise ConflictError(
                f"Curation for field {curation.target_index} already exists."
            ) from dke
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
    async with managed_transaction(db.client) as txn:
        await update_curation_crud(
            db, curation_id=curation_id, updates={"approved_by": approved_by},
            session=txn
        )
        # sync data to sample object after update
        await sync_curation_summary_for_analysis(
            db, sample_id=curation['sample_id'], analysis_id=curation['analysis_id'], session=txn
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
    
    async with managed_transaction(db.client) as txn:
        await delete_curation_crud(db, curation_id=curation_id, session=txn)

        # sync changes to sample object
        await sync_curation_summary_for_analysis(
            db, sample_id=curation['sample_id'], analysis_id=curation['analysis_id'], session=txn
        )
    
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


async def sync_curation_summary_for_analysis(
    db: Database,
    *,
    sample_id: str,
    analysis_id: str,
    session: ClientSession | None = None
):
    """Re-sync the the curation summary for one analysis result."""
    # Fetch all curations for this analysis from canonical collection
    curations = await get_curations_crud(
        db,
        filters={"analysis_id": analysis_id},
        session=session
    )

    items_idx = defaultdict(list)
    # Group curations by target summary field
    for cur in curations:
        analysis_type = cur["analysis_type"]
        field_name = group_for(analysis_type)
        # Strip redundant IDs when embedding in sample object
        # (context is implicit in the nested structure)
        cur_copy = cur.copy()
        cur_copy.pop("sample_id", None)
        cur_copy.pop("analysis_id", None)
        cur_copy.pop("analysis_type", None)
        items_idx[(field_name, analysis_type)].append(cur_copy)
    
    ops: list[UpdateOne] = []
    for (field_name, at), items in items_idx.items():
        filter_ = {
            "sample_id": sample_id,
            field_name: {
                "$elemMatch": {
                    "analysis_id": analysis_id, 
                    "analysis_type": at
                }
            }
        }
        # Store curations without redundant ID fields
        ops.append(UpdateOne(
            filter_,
            {"$set": {f"{field_name}.$.curations": items}}
        ))
    
    ops.append(
        UpdateOne(
            {"sample_id": sample_id}, 
            {"$set": {"modified_at": get_timestamp()}}
        )
    )

    result = await db.sample_collection.bulk_write(
        ops, ordered=True, session=session
    )
    if result.matched_count == 0:
        raise EntryNotFound(f"No sample with {sample_id}")
    return bool(result.acknowledged)
