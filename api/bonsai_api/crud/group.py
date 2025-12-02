"""Functions for conducting CURD operations on group collection"""

import logging
from typing import Any

from api_client.audit_log.client import AuditLogClient
from api_client.audit_log.models import SourceType, Subject
from bonsai_api.db import Database
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.group import GroupInCreate, GroupInfoDatabase
from bonsai_api.models.sample import SampleSummary
from bonsai_api.utils import get_timestamp
from prp.models.typing import TypingMethod
from pydantic import ValidationError
from pymongo import ASCENDING, ReturnDocument, UpdateOne
from pymongo.errors import BulkWriteError, DuplicateKeyError, PyMongoError

from .errors import DatabaseOperationError, EntryNotFound
from .tags import compute_phenotype_tags
from .utils import audit_event_context

LOG = logging.getLogger(__name__)


def group_document_to_db_object(document: dict[str, Any]) -> GroupInfoDatabase:
    """Convert document from database to GroupInfoDatabase object."""
    try:
        inserted_id = document.pop("_id", None)
        if inserted_id is not None:
            document["id"] = str(inserted_id)
        return GroupInfoDatabase.model_validate(document)
    except ValidationError as ve:
        LOG.error("Validation error while converting group document: %s", str(ve))
        raise ValueError(f"Invalid data in group document: {str(ve)}") from ve


async def get_groups(
    db: Database,
    filter_: dict[str, Any] | None = None,
    projection: dict[str, str | int] | None = None,
    skip: int = 0,
    limit: int | None = 100,
    sort: list[tuple[str, int]] | None = None,
    batch_size: int = 100,
    session: Any = None,
) -> list[GroupInfoDatabase]:
    """Get collections from database.

    Retrieve groups with optional filtering, projection and pagination.
    - filter_: MongoDB filter dictionary.
    - projection: fields to include/exclude.
    - limit: max results to return; use None for no limit (but avoid for large collections).
    - skip: documents to skip (offset pagination).
    - sort: list of tuples like [('created_at', ASCENDING)].
    - batch_size: motor cursor batch size for streaming.
    """
    filter_ = filter_ or {}
    projection = projection or None
    try:
        cursor = (
            db.sample_group_collection.find(filter_, projection, session=session)
            .skip(skip)
            .batch_size(batch_size)
        )
        if limit:
            cursor = cursor.limit(limit)

        if sort:
            cursor = cursor.sort(sort)

        groups = []
        async for doc in cursor:
            try:
                groups.append(group_document_to_db_object(doc))
            except ValueError as ve:
                LOG.error("Skipping invalid group document: %s", str(ve))
                continue
    except PyMongoError as pme:
        LOG.error("MongoDB error while retrieving groups: %s", str(pme))
        raise DatabaseOperationError(
            f"Database error occurred while retrieving groups: {str(pme)}"
        ) from pme
    return groups


async def check_group_exists(db: Database, group_id: str, session: Any = None) -> bool:
    """Check if group with group_id exists in database."""
    if not group_id:
        return False
    doc = await db.sample_group_collection.find_one(
        {"group_id": group_id}, {"_id": 1}, session=session
    )
    return doc is not None


def _build_sample_lookup_stages() -> list[dict[str, Any]]:
    """Build MongoDB stagest for sample lookup and transformation.

    Returns a list of pipeline stages to:
    1. Look up sample documents by sample_id
    2. Filter typing results (optionally exclude CGMLST)
    3. Extract primary species from predictions
    4. Sort samples by creation date
    """
    return [
        {
            "$lookup": {
                "from": "sample",
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
                                    # Filter out cgMLST results to redcuce response size
                                    "cond": {
                                        "$ne": [
                                            "$$result.type",
                                            TypingMethod.CGMLST.value,
                                        ]
                                    },
                                }
                            },
                            # Extract the first, primary, species from species prediction array
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


def _build_group_aggregation_pipeline(
    group_id: str, lookup_samples: bool
) -> list[dict[str, Any]]:
    """Build the aggregation pipeline for retrieving a group."""
    pipeline = [{"$match": {"group_id": group_id}}]
    if lookup_samples:
        pipeline.extend(_build_sample_lookup_stages())
    return pipeline


def _enrich_group_samples(group: dict[str, Any]) -> None:
    """Compute and attach phenotype tags to each sample in the group.

    Mutates the group dict by adding a "tags" field for each sample.
    Raises ValidationError if sample data is malformed.

    Args:
        group: The group document dict with "included_samples" key.

    Raises:
        ValidationError: If a sample cannot be parsed as SampleSummary.
    """
    samples_with_tags = []
    for sample_data in group.get("included_samples", []):
        try:
            sample_summary = SampleSummary(**sample_data)
            sample_data["tags"] = compute_phenotype_tags(sample_summary)
            samples_with_tags.append(sample_data)
        except ValidationError as ve:
            LOG.warning(
                "Skipping sample %s due to validation error: %s",
                sample_data.get("sample_id"),
                ve,
            )
            # Optionally: skip invalid samples or re-raise
            continue

    group["included_samples"] = samples_with_tags


async def get_group(
    db: Database, group_id: str, lookup_samples: bool = False, session: Any = None
) -> GroupInfoDatabase:
    """Get a single group from the database."""
    if not group_id or not isinstance(group_id, str):
        raise ValueError(
            f"Invalid group_id: must be a non-empty string, got {group_id}"
        )

    try:
        pipeline = _build_group_aggregation_pipeline(group_id, lookup_samples)

        cursor = await db.sample_group_collection.aggregate(pipeline, session=session)
        async for group in cursor:
            if lookup_samples and group.get("included_samples"):
                try:
                    _enrich_group_samples(group)
                except (ValidationError, ValueError) as exc:
                    LOG.warning(
                        "Failed to enrich samples for %s: %s. Skipping.", group_id, exc
                    )
            return group_document_to_db_object(group)
        # Raise error if no group was found
        raise EntryNotFound(group_id)
    except PyMongoError as pme:
        LOG.error("MongoDB error while retrieving group: %s", str(pme))
        raise DatabaseOperationError(
            f"Database error occurred while retrieving group: {str(pme)}"
        ) from pme


async def create_group(
    db: Database,
    group_record: GroupInCreate,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> GroupInfoDatabase:
    """Create a new group document."""
    event_subject = Subject(id=group_record.group_id, type=SourceType.USR)
    with audit_event_context(audit, "create_group", ctx, event_subject):
        try:
            doc = await db.sample_group_collection.insert_one(
                group_record.model_dump(mode="json")
            )
            inserted_id = doc.inserted_id
            db_obj = GroupInfoDatabase(
                id=str(inserted_id),
                **group_record.model_dump(mode="json"),
            )
        except DuplicateKeyError as dke:
            LOG.error("Duplicate key error while creating group: %s", str(dke))
            raise DatabaseOperationError(
                f"Group with id {group_record.group_id} already exists."
            ) from dke
        except PyMongoError as pme:
            LOG.error("MongoDB error while creating group: %s", str(pme))
            raise DatabaseOperationError(
                f"Database error occurred while creating group: {str(pme)}"
            ) from pme
        except ValidationError as ve:
            LOG.error("Validation error while creating group: %s", str(ve))
            raise ValueError(
                f"Invalid data provided for creating group: {str(ve)}"
            ) from ve
    return db_obj


async def delete_group(
    db: Database,
    group_id: str,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> None | int:
    """Delete group with group_id from database."""
    if not group_id:
        return

    event_subject = Subject(id=group_id, type=SourceType.USR)
    meta = {"group_id": group_id}
    with audit_event_context(audit, "delete_group", ctx, event_subject):
        async with db.client.start_session() as session:
            try:
                txn = await session.start_transaction()
                async with txn:
                    existing = await check_group_exists(db, group_id, session=session)
                    if not existing:
                        raise EntryNotFound(group_id)

                    # Remove group document
                    group_res = await db.sample_group_collection.delete_one(
                        {"group_id": group_id}, session=session
                    )
                    if group_res.deleted_count == 0:
                        raise EntryNotFound(group_id)

                    # Remove group from sample membership collection
                    membership_res = (
                        await db.sample_group_membership_collection.update_many(
                            {"$pull": {"groups": {"group_id": group_id}}},
                            session=session,
                        )
                    )
                    meta.update({"membership_deleted": membership_res.modified_count})

                    return group_res.deleted_count
            except PyMongoError as pme:
                LOG.error("MongoDB error while deleting group: %s", str(pme))
                raise DatabaseOperationError(
                    f"Database error occurred while deleting group: {str(pme)}"
                ) from pme


async def update_group(
    db: Database,
    group_id: str,
    group_record: GroupInCreate,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> GroupInfoDatabase:
    """Update information of group."""
    payload = group_record.model_dump(mode="json")
    if not payload:
        # Nothing to update, return current document
        exsting = await get_group(db, group_id)
        if not exsting:
            raise EntryNotFound(group_id)
        return GroupInfoDatabase.model_validate(exsting)

    payload["modified_at"] = get_timestamp()
    # update info in database
    event_subject = Subject(id=group_id, type=SourceType.USR)
    with audit_event_context(audit, "update_group", ctx, event_subject):
        try:
            updated = await db.sample_group_collection.find_one_and_update(
                {"group_id": group_id},
                {"$set": payload},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as pme:
            LOG.error("MongoDB error while updating group: %s", str(pme))
            raise DatabaseOperationError(
                f"Database error occurred while updating group: {str(pme)}"
            ) from pme

        if not updated:
            raise EntryNotFound(group_id)

    return GroupInfoDatabase.model_validate(updated)


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
                txn = await session.start_transaction()
                async with txn:
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
                    group_entry = {
                        "group_id": group_record.group_id,
                        "display_name": group_record.display_name,
                    }
                    for sid in sample_ids:
                        ops.append(
                            UpdateOne(
                                {"sample_id": sid},
                                {"$addToSet": {"groups": group_entry}},
                                upsert=True,
                            )
                        )

                    if ops:
                        await db.sample_group_membership_collection.bulk_write(
                            ops, ordered=False, session=session
                        )
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

    existing = await check_group_exists(db, group_id)
    if not existing:
        raise EntryNotFound(group_id)

    event_subject = Subject(id=group_id, type=SourceType.USR)
    meta = {"sample_ids": sample_ids}
    with audit_event_context(audit, "add_samples_to_group", ctx, event_subject, meta):
        async with db.client.start_session() as session:
            try:
                txn = await session.start_transaction()
                async with txn:
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
                LOG.error(
                    "Bulk write error while removing samples from group membership: %s",
                    bwe.details,
                )
                raise DatabaseOperationError(
                    f"Errors occurred while removing samples from group membership: {bwe.details}"
                ) from bwe
            except PyMongoError as pme:
                LOG.error(
                    "MongoDB error while removing samples from group: %s", str(pme)
                )
                raise DatabaseOperationError(
                    f"Database error occurred while removing samples from group: {str(pme)}"
                ) from pme
