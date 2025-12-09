"""Manage relationships between samples and groups."""

import logging
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError, PyMongoError
from pymongo.client_session import ClientSession

from .utils import check_groups_exists, managed_transaction
from bonsai_api.db import Database

from bonsai_api.utils import get_timestamp
from bonsai_api.models.memberships import GroupSampleLink, SampleGroupLink

from .errors import DatabaseOperationError, EntryNotFound


LOG = logging.getLogger(__name__)


async def add_memberships(
    db: Database, links: list[SampleGroupLink],
    *, session: ClientSession | None = None
) -> None:
    """Add new group memberships."""
    if not links:
        return

    async def _do_work(db: Database, links: list[SampleGroupLink], session: ClientSession) -> None:
        # verify that group exists
        gids = {gid for lnk in links for gid in lnk.group_ids}
        missing_gids = check_groups_exists(db, gids, session)
        if missing_gids:
            # Abort the transaction if non-existant group was provided
            raise EntryNotFound(f"Unkown group_id(s): {sorted(missing_gids)}")

        # update modified timestamp in document
        await db.sample_group_collection.update_many(
            {"group_id": {"$in": list(gids)}},
            {"$set": {"modified_at": get_timestamp()}},
            session=session,
        )
        # prepare bulk operations to add group membership to samples
        ops = []
        for lnk in links:
            ops.append(UpdateOne(
                {"sample_id": lnk.sample_id},
                {"$addToSet": {"groups": {"$each": lnk.group_ids}}},
                upsert=False
            ))
        if ops:
            await db.sample_collection.bulk_write(ops, ordered=False, session=session)

    try:
        async with managed_transaction(db.client, session) as sess:
            await _do_work(db, links, session=sess)
    except BulkWriteError as bwe:
        LOG.error(
            "Bulk write error while adding samples to group membership: %s",
            bwe.details,
        )
        raise DatabaseOperationError(
            f"Errors occurred while adding samples to group membership: {bwe.details}"
        ) from bwe
    except PyMongoError as pme:
        LOG.error("MongoDB error while adding samples to group: %s", str(pme))
        raise DatabaseOperationError(
            f"Database error occurred while adding samples to group: {str(pme)}"
        ) from pme


async def remove_memberships(
    db: Database,
    links: list[SampleGroupLink],
    *,
    session: ClientSession | None = None
) -> None:
    """Remove group memberships."""
    if not links:
        return

    async def _do_work(db: Database, links: list[SampleGroupLink], session: ClientSession) -> None:
        # verify that group exists
        gids = {gid for lnk in links for gid in lnk.group_ids}
        missing_gids = check_groups_exists(db, gids, session)
        if missing_gids:
            # Abort the transaction if non-existant group was provided
            raise EntryNotFound(f"Unkown group_id(s): {sorted(missing_gids)}")
        
        # Update modified timestamp in group object
        await db.sample_group_collection.update_many(
            {"group_id": {"$in": list(gids)}},
            {"$set": {"modified_at": get_timestamp()}},
            session=session,
        )

        # Prepare bulk operations to add group membership to samples
        ops = []
        for lnk in links:
            ops.append(UpdateOne(
                {"sample_id": lnk.sample_id},
                {"$pullAll": {"groups": lnk.group_ids}},
                upsert=False
            ))
        if ops:
            await db.sample_collection.bulk_write(ops, ordered=False, session=session)
    
    try:
        async with managed_transaction(db.client, session) as sess:
            return await _do_work(db, links, session=sess)
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
    db: Database, sample_ids: list[str]
) -> list[SampleGroupLink]:
    """Get group membership for a list of sample IDs.

    Returns a mapping of sample_id to list of group_ids the sample belongs to.
    """
    if not sample_ids:
        return []
    
    cursor = await db.sample_collection.find(
        {"sample_id": {"$in": sample_ids}}, {"_id": 0, "sample_id": 1, "groups": 1})

    result = []
    async for doc in cursor:
        result.append(SampleGroupLink(sample_id=doc['sample_id'], group_ids=doc['groups']))
    # ensure requested ids are present in ouput
    return result


async def get_samples_by_group_ids(
    db: Database, group_ids: list[str]
) -> list[GroupSampleLink]:
    """Get group membership for a list of sample IDs.

    Returns a mapping of sample_id to list of group_ids the sample belongs to.
    """
    if not group_ids:
        return []

    missing_gids = check_groups_exists(db, group_ids)
    if missing_gids:
        # Abort the transaction if non-existant group was provided
        raise EntryNotFound(f"Unkown group_id(s): {sorted(missing_gids)}")

    pipeline = [
        {"$match": {"groups": {"$in": group_ids}}},
        {"$project": {"_id": 0, "sample_id": 1, "groups": 1}},
        {"$unwind": "groups"},
        {"$match": {"groups": {"$in": group_ids}}},
        {"$group": {"_id": "$groups", "sample_ids": {"$addToSet": "$sample_id"}}},
        {"$project": {"_id": 0, "group_id": "$_id", "sample_ids": 1}},
    ]

    cursor = await db.sample_collection.aggregate(pipeline)

    result: list[GroupSampleLink] = []
    async for doc in cursor:
        result.append(GroupSampleLink.model_validate(doc))

    # ensure requested ids are present in ouput
    return result
