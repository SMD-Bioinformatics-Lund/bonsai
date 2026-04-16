"""Service for managing group memberships.

This module contains orchestration and transaction logic for adding/removing
sample-group memberships. It calls lightweight CRUD helpers to perform DB
operations and keeps transaction boundaries here to avoid circular imports.
"""

import logging
from collections import defaultdict
from datetime import datetime
from itertools import groupby
from typing import Literal

from bonsai_api.crud.group import check_groups_exists
from bonsai_api.crud.memberships import (
    find_groups_by_sample_ids,
    find_samples_by_group_ids,
)
from bonsai_api.crud.sample import check_samples_exists
from bonsai_api.crud.utils import managed_transaction
from bonsai_api.db import Database
from bonsai_api.exceptions import DatabaseOperationError, EntryNotFound
from bonsai_api.models.memberships import MembershipEdge, MembershipEdges
from bonsai_api.utils import get_timestamp
from pymongo import UpdateOne
from pymongo.client_session import ClientSession
from pymongo.errors import BulkWriteError, PyMongoError

LOG = logging.getLogger(__name__)

ValidModes = Literal["add", "remove"]


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
    missing_groups = await check_groups_exists(db, group_ids=group_ids, session=session)
    if missing_groups:
        raise EntryNotFound(f"Unknown group_id(s): {sorted(missing_groups)}")
    missing_samples = await check_samples_exists(
        db, sample_ids=sample_ids, session=session
    )
    if missing_samples:
        raise EntryNotFound(f"Unknown sample_id(s): {sorted(missing_samples)}")


def _compute_delta(
    edges: MembershipEdges, present: dict[str, set[str]], mode: ValidModes
) -> tuple[dict[str, set[str]], dict[str, int]]:
    """Compute the delta between existing sample-group edges and the desired change.

    Returns:
      - per-sample group membership to mutate
      - per-group counter deltas
    """
    per_sample: dict[str, set[str]] = defaultdict(set)
    per_group_delta: dict[str, int] = defaultdict(int)

    if mode == "add":
        for e in edges:
            if e.group_id not in present.get(e.sample_id, set()):
                per_sample[e.sample_id].add(e.group_id)
        for _, gids in per_sample.items():
            for gid in gids:
                per_group_delta[gid] += 1

    else:  # remove
        for e in edges:
            if e.group_id in present.get(e.sample_id, set()):
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
    edges: MembershipEdges, mode: ValidModes, *, db: Database, session: ClientSession
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
    sid_edges = await db.sample_collection.find(
        {"sample_id": {"$in": sample_ids}},
        {"_id": 0, "sample_id": 1, "groups": 1},
        session=session,
    ).to_list(None)

    # convert to MembershipEdge list for grouping
    sid_edge_objs: list[MembershipEdge] = []
    for doc in sid_edges:
        for gid in doc.get("groups", []):
            sid_edge_objs.append(
                MembershipEdge(sample_id=doc["sample_id"], group_id=gid)
            )

    present: dict[str, set[str]] = {
        sid: {e.group_id for e in grp}
        for sid, grp in groupby(sid_edge_objs, lambda e: e.sample_id)
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
            return await _mutate_memberships(edges, mode="remove", db=db, session=sess)
    except BulkWriteError as bwe:
        LOG.error(
            "Bulk write error while removing samples from group: %s",
            bwe.details,
        )
        raise DatabaseOperationError(
            f"Errors occurred while removing samples from group: {bwe.details}"
        ) from bwe
    except PyMongoError as pme:
        LOG.error("MongoDB error while removing samples from group: %s", str(pme))
        raise DatabaseOperationError(
            f"Database error occurred while removing samples from group: {str(pme)}"
        ) from pme


async def get_groups_by_sample_ids(
    db: Database, *, sample_ids: list[str], session: ClientSession | None = None
) -> MembershipEdges:
    """Get group membership for a list of sample IDs.

    Returns a list of MembershipEdge representing membership relations.
    """
    if not sample_ids:
        return []

    missing_sids = await check_samples_exists(
        db, sample_ids=sample_ids, session=session
    )
    if missing_sids:
        # Abort the operation if non-existent sample was provided
        raise EntryNotFound(f"Unknown sample_id(s): {sorted(missing_sids)}")

    edges: MembershipEdges = []
    for doc in await find_groups_by_sample_ids(
        db, sample_ids=sample_ids, session=session
    ):
        for gid in doc.get("groups", []):
            edges.append(MembershipEdge(sample_id=doc["sample_id"], group_id=gid))
    return edges


async def get_samples_by_group_ids(
    db: Database, *, group_ids: list[str], session: ClientSession | None = None
) -> MembershipEdges:
    """Get group membership for a list of group IDs.

    Returns a list of MembershipEdge representing membership relations.
    """
    if not group_ids:
        return []

    missing_gids = await check_groups_exists(db, group_ids=group_ids, session=session)
    if missing_gids:
        # Abort the operation if non-existent group was provided
        raise EntryNotFound(f"Unknown group_id(s): {sorted(missing_gids)}")

    result: MembershipEdges = []
    for doc in await find_samples_by_group_ids(
        db, group_ids=group_ids, session=session
    ):
        result.append(MembershipEdge.model_validate(doc))

    return result
