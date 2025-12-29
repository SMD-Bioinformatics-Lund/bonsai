"""CRUD operations for user favorite groups."""

import logging
from typing import Any, List

from bonsai_api.db import Database
from bonsai_api.utils import get_timestamp
from pymongo.errors import PyMongoError

from .errors import DatabaseOperationError

LOG = logging.getLogger(__name__)


async def add_favorite(db: Database, user_id: str, group_id: str) -> dict[str, Any]:
    """Add a favorite mapping for user->group.

    Returns the created document or existing document.
    """
    if not user_id or not group_id:
        raise ValueError("user_id and group_id required")

    col = db.group_favorite_collection
    if col is None:
        raise DatabaseOperationError("Favorites collection not configured")

    doc = {"user_id": user_id, "group_id": group_id, "created_at": get_timestamp()}
    try:
        # upsert by user+group to make operation idempotent
        await col.update_one({"user_id": user_id, "group_id": group_id}, {"$setOnInsert": doc}, upsert=True)
        return doc
    except PyMongoError as pme:
        LOG.error("MongoDB error while adding favorite: %s", str(pme))
        raise DatabaseOperationError(f"Database error occurred while adding favorite: {str(pme)}") from pme


async def remove_favorite(db: Database, user_id: str, group_id: str) -> int:
    """Remove a favorite mapping. Returns the number of removed docs."""
    col = db.group_favorite_collection
    if col is None:
        raise DatabaseOperationError("Favorites collection not configured")

    try:
        res = await col.delete_one({"user_id": user_id, "group_id": group_id})
        return res.deleted_count
    except PyMongoError as pme:
        LOG.error("MongoDB error while removing favorite: %s", str(pme))
        raise DatabaseOperationError(f"Database error occurred while removing favorite: {str(pme)}") from pme


async def list_user_favorites(db: Database, user_id: str) -> List[str]:
    """Return list of group_ids favorited by user."""
    col = db.group_favorite_collection
    if col is None:
        raise DatabaseOperationError("Favorites collection not configured")

    try:
        cursor = col.find({"user_id": user_id}, {"_id": 0, "group_id": 1})
        docs = await cursor.to_list(None)
        return [d["group_id"] for d in docs]
    except PyMongoError as pme:
        LOG.error("MongoDB error while listing favorites: %s", str(pme))
        raise DatabaseOperationError(f"Database error occurred while listing favorites: {str(pme)}") from pme


async def is_favorite(db: Database, user_id: str, group_id: str) -> bool:
    """Return True if user has favorited the group."""
    col = db.group_favorite_collection
    if col is None:
        raise DatabaseOperationError("Favorites collection not configured")

    try:
        doc = await col.find_one({"user_id": user_id, "group_id": group_id}, {"_id": 0})
        return doc is not None
    except PyMongoError as pme:
        LOG.error("MongoDB error while checking favorite: %s", str(pme))
        raise DatabaseOperationError(f"Database error occurred while checking favorite: {str(pme)}") from pme
