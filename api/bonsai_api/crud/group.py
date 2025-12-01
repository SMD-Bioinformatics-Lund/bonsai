"""Functions for conducting CURD operations on group collection"""

import logging
from typing import Any
from pymongo import UpdateOne, ASCENDING
from pymongo.errors import BulkWriteError, PyMongoError

from api_client.audit_log.client import AuditLogClient
from api_client.audit_log.models import SourceType, Subject
from bonsai_api.db import Database
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.group import GroupInCreate, GroupInfoDatabase
from bonsai_api.models.sample import SampleSummary
from bonsai_api.utils import get_timestamp
from prp.models.typing import TypingMethod

from .errors import EntryNotFound, UpdateDocumentError
from .tags import compute_phenotype_tags
from .utils import audit_event_context

LOG = logging.getLogger(__name__)


def group_document_to_db_object(document: dict[str, Any]) -> GroupInfoDatabase:
    """Convert document from database to GroupInfoDatabase object."""
    inserted_id = document["_id"]
    db_obj = GroupInfoDatabase(
        id=str(inserted_id),
        **document,
    )
    return db_obj


async def get_groups(db: Database) -> list[GroupInfoDatabase]:
    """Get collections from database."""
    cursor = db.sample_group_collection.find({})
    groups = []
    for row in await cursor.to_list(length=100):
        groups.append(group_document_to_db_object(row))
    return groups


async def get_group(
    db: Database, group_id: str, lookup_samples: bool = False
) -> GroupInfoDatabase:
    """Get collections from database."""
    # make aggregation pipeline
    pipeline = [
        {"$match": {"group_id": group_id}},
    ]
    if lookup_samples:
        pipeline.extend(
            [
                {
                    "$lookup": {
                        "from": db.sample_collection.name,
                        "localField": "included_samples",
                        "foreignField": "sample_id",
                        "as": "included_samples",
                        "pipeline": [
                            {
                                "$addFields": {
                                    "typing_result": {
                                        "$filter": {
                                            "input": "typing_result",
                                            "as": "result",
                                            "cond": {
                                                "$ne": [
                                                    "$$result.type",
                                                    TypingMethod.CGMLST.value,
                                                ]
                                            },
                                        }
                                    },
                                    "major_specie": {"$first": "species_prediction"},
                                }
                            },
                            {
                                "$sort": {"created_at": ASCENDING},
                            },
                        ],
                    }
                }
            ]
        )
    async for group in db.sample_group_collection.aggregate(pipeline):
        # compute tags for samples if samples are included
        if lookup_samples:
            for sample in group["included_samples"]:
                # cast as static object
                group["tags"] = compute_phenotype_tags(SampleSummary(**sample))
        return group_document_to_db_object(group)
    raise EntryNotFound(group_id)


async def create_group(
    db: Database,
    group_record: GroupInCreate,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> GroupInfoDatabase:
    """Create a new group document."""
    # add to db
    event_subject = Subject(id=group_record.group_id, type=SourceType.USR)
    with audit_event_context(audit, "create_group", ctx, event_subject):
        doc = await db.sample_group_collection.insert_one(group_record.model_dump())
        inserted_id = doc.inserted_id
        db_obj = GroupInfoDatabase(
            id=str(inserted_id),
            **group_record.model_dump(),
        )
    return db_obj


async def delete_group(
    db: Database,
    group_id: str,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> int:
    """Delete group with group_id from database."""
    event_subject = Subject(id=group_id, type=SourceType.USR)
    with audit_event_context(audit, "delete_group", ctx, event_subject):
        doc = await db.sample_group_collection.delete_one({"group_id": group_id})
        if doc.deleted_count == 0:
            raise EntryNotFound(group_id)
    return doc.deleted_count


async def update_group(
    db: Database,
    group_id: str,
    group_record: GroupInCreate,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> GroupInfoDatabase:
    """Update information of group."""
    # update info in database
    event_subject = Subject(id=group_id, type=SourceType.USR)
    with audit_event_context(audit, "update_group", ctx, event_subject):
        update_obj = await db.sample_group_collection.update_one(
            {"group_id": group_id},
            {
                "$set": {"modified_at": get_timestamp(), **group_record.model_dump()},
            },
        )

        if not update_obj.matched_count == 1:
            raise EntryNotFound(group_id)
        if not update_obj.modified_count == 1:
            raise UpdateDocumentError(group_id)

    return update_obj.modified_count


async def update_image(db: Database, image: GroupInCreate) -> GroupInfoDatabase:
    """Create a new collection document."""
    # cast input data as the type expected to insert in the database
    db_obj = await db.sample_group_collection.insert_one(image.model_dump())
    return db_obj


async def add_samples_to_group(
    db: Database,
    group_id: str,
    sample_ids: list[str],
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> None:
    """Create a new collection document."""
    if not sample_ids:
        return

    group_record = await get_group(db, group_id)
    if not group_record:
        raise EntryNotFound(group_id)

    # Prepare audit log context
    event_subject = Subject(id=group_id, type=SourceType.USR)
    meta = {"sample_ids": sample_ids}
    with audit_event_context(audit, "add_samples_to_group", ctx, event_subject, meta):
        async with db.client.start_session() as session:
            try:
                async with session.start_transaction():
                    # Update group document
                    await db.sample_group_collection.update_one(
                        {"group_id": group_id},
                        {
                            "$set": {"modified_at": get_timestamp()},
                            "$addToSet": {
                                "included_samples": {"$each": sample_ids},
                            },
                        },
                        session=session,
                    )
                    # prepare bulk operations to add group membership to samples
                    ops = []
                    group_entry = {"group_id": group_record.group_id, "display_name": group_record.display_name}
                    for sid in sample_ids:
                        ops.append(UpdateOne({"sample_id": sid}, {"$addToSet": {"groups": group_entry}}, upsert=True))

                    if ops:
                        await db.sample_group_membership_collection.bulk_write(ops, ordered=False, session=session)
            except BulkWriteError as bwe:
                LOG.error("Bulk write error while adding samples to group membership: %s", bwe.details)
                raise UpdateDocumentError(f"Errors occurred while adding samples to group membership: {bwe.details}") from bwe
            except PyMongoError as pme:
                LOG.error("MongoDB error while adding samples to group: %s", str(pme))
                raise UpdateDocumentError(f"Database error occurred while adding samples to group: {str(pme)}") from pme


async def remove_samples_from_group(
    db: Database,
    group_id: str,
    sample_ids: list[str],
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> None:
    """Create a new collection document."""
    if not sample_ids:
        return

    group_record = await get_group(db, group_id)
    if not group_record:
        raise EntryNotFound(group_id)

    event_subject = Subject(id=group_id, type=SourceType.USR)
    meta = {"sample_ids": sample_ids}
    with audit_event_context(audit, "add_samples_to_group", ctx, event_subject, meta):
        async with db.client.start_session() as session:
            try:
                async with session.start_transaction():
                    await db.sample_group_collection.update_one(
                        {"group_id": group_id},
                        {
                            "$set": {"modified_at": get_timestamp()},
                            "$pull": {
                                "included_samples": {"$in": sample_ids},
                            },
                        },
                        session=session,
                    )
                # prepare to remove group from sample membership collection
                ops = []
                for sid in sample_ids:
                    ops.append(
                        UpdateOne(
                            {"sample_id": sid},
                            {"$pull": {"groups": {"group_id": group_id}}},
                        )
                    )
                if ops:
                    await db.sample_group_membership_collection.bulk_write(ops)
            except BulkWriteError as bwe:
                LOG.error("Bulk write error while removing samples from group membership: %s", bwe.details)
                raise UpdateDocumentError(f"Errors occurred while removing samples from group membership: {bwe.details}") from bwe
            except PyMongoError as pme:
                LOG.error("MongoDB error while removing samples from group: %s", str(pme))
                raise UpdateDocumentError(f"Database error occurred while removing samples from group: {str(pme)}") from pme
