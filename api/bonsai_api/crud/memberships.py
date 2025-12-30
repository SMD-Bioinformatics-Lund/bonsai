"""Manage relationships between samples and groups.

This module contains lightweight helpers for fetching membership mappings from
the database.
"""

import logging
from typing import Any
from pymongo.client_session import ClientSession

from bonsai_api.db import Database

LOG = logging.getLogger(__name__)


async def find_groups_by_sample_ids(
    db: Database, *, sample_ids: list[str], session: ClientSession | None = None
) -> list[dict[str, Any]]:
    """Get group membership for a list of sample IDs.

    Returns a list of MembershipEdge representing membership relations.
    """
    if not sample_ids:
        return []

    cursor = db.sample_collection.find(
        {"sample_id": {"$in": sample_ids}},
        {"_id": 0, "sample_id": 1, "groups": 1},
        session=session,
    )
    return await cursor.to_list(None)


async def find_samples_by_group_ids(
    db: Database, *, group_ids: list[str], session: ClientSession | None = None
) -> list[dict[str, Any]]:
    """Get group membership for a list of group IDs.

    Returns a list of MembershipEdge representing membership relations.
    """
    if not group_ids:
        return []

    pipeline = [
        {"$match": {"groups": {"$in": group_ids}}},
        {"$project": {"_id": 0, "sample_id": 1, "group_id": "$groups"}},
        {"$unwind": "$group_id"},
    ]

    cursor = await db.sample_collection.aggregate(pipeline, session=session)
    return await cursor.to_list(None)
