"""Functions for conducting CURD operations on group collection"""
import logging
from datetime import datetime
from typing import Any, Dict, List

from prp.models.typing import TypingMethod
from pymongo import ASCENDING

from ..db import Database
from ..models.group import (GroupInCreate, GroupInfoDatabase,
                            OverviewTableColumn)
from ..models.sample import SampleSummary
from .errors import EntryNotFound, UpdateDocumentError
from .sample import get_sample
from .tags import compute_phenotype_tags

LOG = logging.getLogger(__name__)


def group_document_to_db_object(document: Dict[str, Any]) -> GroupInfoDatabase:
    """Convert document from database to GroupInfoDatabase object."""
    inserted_id = document["_id"]
    db_obj = GroupInfoDatabase(
        id=str(inserted_id),
        **document,
    )
    return db_obj


async def get_groups(db: Database) -> List[GroupInfoDatabase]:
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


async def create_group(db: Database, group_record: GroupInCreate) -> GroupInfoDatabase:
    """Create a new group document."""
    # add to db
    doc = await db.sample_group_collection.insert_one(group_record.model_dump())
    inserted_id = doc.inserted_id
    db_obj = GroupInfoDatabase(
        id=str(inserted_id),
        **group_record.model_dump(),
    )
    return db_obj


async def delete_group(db: Database, group_id: str) -> bool:
    """Delete group with group_id from database."""
    doc = await db.sample_group_collection.delete_one({"group_id": group_id})
    if doc.deleted_count == 0:
        raise EntryNotFound(group_id)
    return doc.deleted_count


async def update_group(
    db: Database, group_id: str, group_record: GroupInCreate
) -> GroupInfoDatabase:
    """Update information of group."""
    # update info in database
    update_obj = await db.sample_group_collection.update_one(
        {"group_id": group_id},
        {
            "$set": {"modified_at": datetime.now(), **group_record.model_dump()},
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


async def append_sample_to_group(db: Database, sample_id: str, group_id: str) -> None:
    """Create a new collection document."""
    sample_obj = await get_sample(db, sample_id)
    update_obj = await db.sample_group_collection.update_one(
        {"group_id": group_id},
        {
            "$set": {"modified_at": datetime.now()},
            "$addToSet": {
                "included_samples": sample_obj.sample_id,
            },
        },
    )
    if not update_obj.matched_count == 1:
        raise EntryNotFound(group_id)
    if not update_obj.modified_count == 1:
        raise UpdateDocumentError(group_id)
