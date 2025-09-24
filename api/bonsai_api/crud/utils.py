"""Generic database functions."""

from typing import Any
from motor.motor_asyncio import AsyncIOMotorCollection

async def get_deprecated_records(collection: AsyncIOMotorCollection, schema_version: int) -> list[dict[str, Any]]:
    """Get documents from the collection that have a schema version."""
    cursor = collection.find({"$or": [
        {"schema_version": {"$lt": schema_version}},
        {"schema_version": {"$exists": False}}
    ]})
    return [dict(doc) for doc in await cursor.to_list(None)]
