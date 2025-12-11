"""Manage relationships between samples and groups."""

import logging
from collections import defaultdict
from datetime import datetime
from itertools import groupby
from typing import Literal

from bonsai_api.db import Database
from bonsai_api.models.memberships import MembershipEdge, MembershipEdges
from bonsai_api.utils import get_timestamp
from pymongo import UpdateOne
from pymongo.client_session import ClientSession
from pymongo.errors import BulkWriteError, PyMongoError

from .errors import DatabaseOperationError, EntryNotFound
from .utils import check_groups_exists, check_samples_exists, managed_transaction

LOG = logging.getLogger(__name__)


ValidModes = Literal["add", "remvoe"]


def _dedupe_edges(edges: MembershipEdges) -> MembershipEdges:
    """Remove duplicate edges."""
    seen: set[tuple[str, str]] = set()
    out: MembershipEdges = []
    for edge in edges:
        key = (edge.sample_id, edge.group_id)
        if edge.sample_id and edge.group_id and key not in seen:
            seen.add(key)
            out.append(edge)
    return out


async def _check_exists(
    db: Database,
    sample_ids: list[str],
    group_ids: list[str],
    *,
    session: ClientSession | None,
) -> None:
    """Convenience wrapper for checking if samples and groups exists"""
    missing_groups = await check_groups_exists(db, group_ids, session)  # set[str]
    if missing_groups:
        raise EntryNotFound(f"Unknown group_id(s): {sorted(missing_groups)}")
    missing_samples = await check_samples_exists(db, sample_ids, session)  # set[str]
    if missing_samples:
        raise EntryNotFound(f"Unknown sample_id(s): {sorted(missing_samples)}")


def _compute_delta(
    edges: MembershipEdges, present: dict[str, set[str]], mode: ValidModes
) -> tuple[dict[str, set[str]], dict[str, int]]:
    """Compute the delta between exising sample-group edges and the desired change.

    Returns:
      - per-sample group membership to mutate
      - per-group counter deltas
    """
    per_sample: dict[str, set[str]] = defaultdict(set)
    per_group_delta: dict[str, int] = defaultdict(int)

    if mode == "add":
        for e in edges:
            if e.group_id not in present[e.sample_id]:
                per_sample[e.sample_id].add(e.group_id)
        for _, gids in per_sample.items():
            for gid in gids:
                per_group_delta[gid] += 1

    else:  # remove
        for e in edges:
            if e.group_id in present[e.sample_id]:
                per_sample[e.sample_id].add(e.group_id)
        for _, gids in per_sample.items():
            for gid in gids:
                per_group_delta[gid] -= 1
    return per_sample, per_group_delta


def _build_sample_ops(
    per_sample: dict[str, set[str]],
    mode: ValidModes,
    ts: datetime,
) -> list[UpdateOne]:
    ops: list[UpdateOne] = []
    for sid, gids in per_sample.items():
        sorted_gids = sorted(gids)
        if mode == "add":
            ops.append(
                UpdateOne(
                    {"sample_id": sid},
                    {
                        "$addToSet": {"groups": {"$each": sorted_gids}},
                        "$set": {"modified_at": ts},
                    },
                    upsert=False,
                )
            )
        else:
            ops.append(
                UpdateOne(
                    {"sample_id": sid},
                    {
                        "$pull": {"groups": {"$in": sorted_gids}},
                        "$set": {"modified_at": ts},
                    },
                    upsert=False,
                )
            )
    return ops


def _build_group_ops(
    per_group_delta: dict[str, int],
    ts: datetime,
) -> list[UpdateOne]:
    ops: list[UpdateOne] = []
    for gid, delta in per_group_delta.items():
        if delta == 0:
            continue
        ops.append(
            UpdateOne(
                {"group_id": gid},
                {"$inc": {"sample_count": delta}, "$set": {"modified_at": ts}},
                upsert=False,
            )
        )
    return ops


async def _mutate_memberships(
    edges: MembershipEdge, mode: ValidModes, *, db: Database, session: ClientSession
) -> None:
    """Generic function for mutating group memberships using a db transaction."""
    if not edges:
        return

    edges = _dedupe_edges(edges)

    # Collect ids
    sample_ids = sorted({e.sample_id for e in edges})
    group_ids = sorted({e.group_id for e in edges})

    # 1. Validate that groups and samples exists
    await _check_exists(db, sample_ids, group_ids, session=session)

    # 2. Fetch existing memberships for the samples implicated
    sid_edges = await get_groups_by_sample_ids(db, sample_ids, session=session)
    present: dict[str, set[str]] = {
        sid: set(gids) for sid, gids in groupby(sid_edges, lambda e: e.sample_id)
    }

    # 3. Compute new edges that shall to be added
    per_sample, per_group_delta = _compute_delta(edges, present, mode=mode)
    if not per_sample:  # nothing to do
        return

    # 4. Build groups to add per sample and per group sample_count increments
    ts = get_timestamp()
    smp_ops = _build_sample_ops(per_sample, mode=mode, ts=ts)
    grp_ops = _build_group_ops(per_group_delta, ts)

    # 5. Bulk update samples and groups
    if smp_ops:
        await db.sample_collection.bulk_write(smp_ops, ordered=False, session=session)

    if grp_ops:
        await db.sample_group_collection.bulk_write(
            grp_ops, ordered=False, session=session
        )


async def add_memberships(
    edges: MembershipEdges, *, db: Database, session: ClientSession | None = None
) -> None:
    """Add new group memberships."""

    try:
        async with managed_transaction(db.client, session) as sess:
            await _mutate_memberships(edges, mode="add", db=db, session=sess)
    except BulkWriteError as bwe:
        LOG.error(
            "Bulk write error while adding membership: %s",
            bwe.details,
        )
        raise DatabaseOperationError(
            f"Errors occurred while adding membership: {bwe.details}"
        ) from bwe
    except PyMongoError as pme:
        LOG.error("MongoDB error while adding memberships: %s", str(pme))
        raise DatabaseOperationError(f"Database error: {str(pme)}") from pme


async def remove_memberships(
    edges: MembershipEdges, *, db: Database, session: ClientSession | None = None
) -> None:
    """Remove group memberships."""
    try:
        async with managed_transaction(db.client, session) as sess:
            return await _mutate_memberships(edges, mode="remvoe", db=db, session=sess)
    except BulkWriteError as bwe:
        LOG.error(
            "Bulk write error while removing samples from group: %s",
            bwe.details,
        )
        raise DatabaseOperationError(
            f"Errors occurred while adding samples to group membership: {bwe.details}"
        ) from bwe
    except PyMongoError as pme:
        LOG.error("MongoDB error while adding samples to group: %s", str(pme))
        raise DatabaseOperationError(
            f"Database error occurred while removing samples from group: {str(pme)}"
        ) from pme


async def get_groups_by_sample_ids(
    sample_ids: list[str], *, db: Database, session: ClientSession | None = None
) -> MembershipEdges:
    """Get group membership for a list of sample IDs.

    Returns a mapping of sample_id to list of group_ids the sample belongs to.
    """
    if not sample_ids:
        return []

    cursor = db.sample_collection.find(
        {"sample_id": {"$in": sample_ids}},
        {"_id": 0, "sample_id": 1, "groups": 1},
        session=session,
    )

    result = []
    async for doc in cursor:
        for gid in doc["groups"]:
            result.append(MembershipEdge(sample_id=doc["sample_id"], group_id=gid))
    # ensure requested ids are present in ouput
    return result


async def get_samples_by_group_ids(
    group_ids: list[str], *, db: Database, session: ClientSession | None = None
) -> MembershipEdges:
    """Get group membership for a list of sample IDs.

    Returns a mapping of sample_id to list of group_ids the sample belongs to.
    """
    if not group_ids:
        return []

    missing_gids = await check_groups_exists(db, group_ids)
    if missing_gids:
        # Abort the transaction if non-existant group was provided
        raise EntryNotFound(f"Unkown group_id(s): {sorted(missing_gids)}")

    pipeline = [
        {"$match": {"groups": {"$in": group_ids}}},
        {"$project": {"_id": 0, "sample_id": 1, "group_id": "$groups"}},
        {"$unwind": "$group_id"},
    ]

    cursor = await db.sample_collection.aggregate(pipeline, session=session)

    result = []
    async for doc in cursor:
        result.append(MembershipEdge.model_validate(doc))

    # ensure requested ids are present in ouput
    return result
