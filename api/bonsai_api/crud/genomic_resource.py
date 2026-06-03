"""Genomic asset CRUD operations."""

from typing import Any

from bonsai_api.db import Database
from pymongo.client_session import ClientSession
from pymongo.results import UpdateResult


async def sample_has_resource(
    db: Database,
    *,
    sample_id: str,
    pipeline_id: str,
    session: ClientSession | None = None
) -> bool:
    """Return True if a sample with id exists."""
    doc = await db.sample_collection.find_one(
        {"genomic_resources.pipeline_id": pipeline_id}, {"_id": 1}, session=session
    )
    return bool(doc)


async def insert_genomic_resource(
    db: Database,
    *,
    sample_id: str,
    resource_data: list[dict[str, Any]],
    session: ClientSession | None = None
):
    """Insert a genomic resource for a sample."""
    await db.sample_collection.update_one( 
        {"sample_id": sample_id},
        {
            "$push": {
                "genomic_resources": {
                    "$each": resource_data
                }
            }
        },
        session=session,
    )


async def get_genomic_resource_by_id(db, resource_id: str, session=None) -> dict[str, Any] | None:
    """Get a genomic resource by ID."""

    doc = await db.sample_collection.find_one(
        {"genomic_resources.id": resource_id},
        session=session
    )

    if not doc:
        return None

    for r in doc.get("genomic_resources", []):
        if r["id"] == resource_id:
            return r

    return None


async def list_genomic_resources_by_sample_id(db, sample_id: str, session=None) -> list[dict[str, Any]]:
    """List genomic resources for a sample."""

    doc = await db.sample_collection.find_one(
        {"sample_id": sample_id},
        session=session,
    )
    if not doc:
        return []
    
    return doc.get("genomic_resources", [])


async def delete_genomic_resource(
    db: Database, *, resource_id: str, session: ClientSession | None = None
) -> UpdateResult:
    """Delete a genomic resource by ID."""
    result = await db.sample_collection.update_one(
        {"genomic_resources.resource_id": resource_id},
        {"$pull": {"genomic_resources": {"resource_id": resource_id}}},
        session=session,
    )
    return result
