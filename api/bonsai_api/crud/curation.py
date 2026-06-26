"""Get or create curation records for analysis results."""

from typing import Any
import logging
from fastapi.encoders import jsonable_encoder
from pymongo.client_session import ClientSession

from bonsai_api.utils import get_timestamp
from bonsai_api.db import Database


LOG = logging.getLogger(__name__)


async def get_curation_by_id_crud(
    db: Database,
    *,
    curation_id: str,
    session: ClientSession | None = None
) -> dict[str, Any] | None:
    """Get a single curation by its ID (primary key lookup)."""
    return await db.curations_collection.find_one({"id": curation_id}, session=session)


async def get_curation_by_analysis_id_crud(
    db: Database,
    *,
    analysis_id: str,
    session: ClientSession | None = None
) -> dict[str, Any] | None:
    """Get a curation by analysis ID (foreign key lookup)."""
    return await db.curations_collection.find_one({"analysis_id": analysis_id}, session=session)


async def get_curations_crud(
    db: Database,
    *,
    filters: dict[str, Any] | None = None,
    limit: int | None = None,
    session: ClientSession | None = None
) -> list[dict[str, Any]]:
    """Query curations."""
    filters = filters or {}
    projection = {"_id": 0}
    cursor = db.curations_collection.find(filters, projection, session=session)
    if limit:
        cursor = cursor.limit(limit)
    return await cursor.to_list(None)


async def create_curation(
    db: Database, *, doc: dict[str, Any], session: ClientSession | None = None
) -> str:
    """Insert an analysis record and return its id."""
    doc_copy = dict(doc)
    doc_copy.setdefault("created_at", get_timestamp())

    res = await db.curations_collection.insert_one(doc_copy, session=session)
    LOG.info(
        "Inserted curation record %s for analysis %s",
        res.inserted_id,
        doc.get("analysis_id"),
    )
    return str(res.inserted_id)


async def update_curation_crud(
    db: Database,
    *,
    curation_id: str,
    updates: dict[str, Any],
    session: ClientSession | None = None,
) -> bool:
    """Update a curation document."""
    updates["modified_at"] = get_timestamp()
    
    result = await db.curations_collection.update_one(
        {"id": curation_id},
        {"$set": updates},
        session=session
    )
    
    return result.modified_count == 1


async def delete_curation_crud(
    db: Database,
    *,
    curation_id: str,
    session: ClientSession | None = None,
) -> bool:
    """Delete a curation document."""
    result = await db.curations_collection.delete_one({"id": curation_id}, session=session)
    return result.deleted_count == 1


async def get_pending_approvals_crud(
    db: Database,
    *,
    analysis_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Get curations pending approval."""
    filters = {"approved_by": None}
    if analysis_types:
        filters["analysis_type"] = {"$in": analysis_types}
    
    return await get_curations_crud(db, filters=filters)
