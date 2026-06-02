"""Genomic asset CRUD operations."""

from typing import Any

from pymongo.client_session import ClientSession

from bonsai_api.db import Database


async def sample_has_resource(
    db: Database, *, sample_id: str, pipeline_id: str, session: ClientSession | None = None
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
    pipeline_id: str,
    resource_data: dict,
    session: ClientSession | None = None
):
    """Insert a genomic resource for a sample."""
    await db.sample_collection.update_one(
        {"sample_id": sample_id},
        {"$push": {"genomic_resources": {
            "pipeline_id": pipeline_id,
            "resource_data": resource_data
        }}},
        session=session
    )


async def get_genomic_resources_by_id(
    db: Database, *, sample_id: str, resource_id: str | None = None, session: ClientSession | None = None
) -> list[dict[str, Any]]:
    """Get a genomic resources by ID."""
    query = {"sample_id": sample_id}
    if sample_id is not None:
        query["sample_"]
    if resource_id is not None:
        query["genomic_resources.resource_id"] = resource_id
    return await db.genomic_resource_collection.find(query, session=session)
):