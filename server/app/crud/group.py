"""Functions for conducting CURD operations on group collection"""
import logging
from random import sample
from bson.objectid import ObjectId
from ..db import Database
from ..models.group import GroupInCreate, GroupInfoDatabase, UpdateIncludedSamples
from typing import Dict, Any, List
from .sample import get_sample
from datetime import datetime

LOG = logging.getLogger(__name__)


def group_document_to_db_object(document: Dict[str, Any]) -> GroupInfoDatabase:
    """Convert document from database to GroupInfoDatabase object."""
    inserted_id = document["_id"]
    db_obj = GroupInfoDatabase(
        id=str(inserted_id),
        created_at=ObjectId(inserted_id).generation_time,
        modified_at=ObjectId(inserted_id).generation_time,
        **document
    )
    return db_obj


async def get_groups(db: Database) -> List[GroupInfoDatabase]:
    """Get collections from database."""
    cursor = db.sample_group_collection.find({})
    groups = []
    for row in await cursor.to_list(length=100):
        groups.append(group_document_to_db_object(row))
    return groups


async def get_group(db: Database, group_id: str) -> GroupInfoDatabase:
    """Get collections from database."""
    group = await db.sample_group_collection.find_one({"groupId": group_id})
    return group_document_to_db_object(group)


async def create_group(db: Database, group_record: GroupInCreate) -> GroupInfoDatabase:
    """Create a new group document."""
    # cast input data as the type expected to insert in the database
    doc = await db.sample_group_collection.insert_one(group_record.dict(by_alias=True))
    inserted_id = doc.inserted_id
    db_obj = GroupInfoDatabase(
        id=str(inserted_id),
        created_at=ObjectId(inserted_id).generation_time,
        modified_at=ObjectId(inserted_id).generation_time,
        **group_record.dict(by_alias=True)
    )
    return db_obj


async def update_image(db: Database, image: GroupInCreate) -> GroupInfoDatabase:
    """Create a new collection document."""
    # cast input data as the type expected to insert in the database
    db_obj = await db.sample_group_collection.insert_one(
        group_record.dict(by_alias=True)
    )
    return db_obj


async def add_sample_to_group(
    db: Database, sample_id: str, group_id: str
) -> GroupInfoDatabase:
    """Create a new collection document."""
    sample_obj = await get_sample(db, sample_id)
    param_included_sample = UpdateIncludedSamples.inlcuded_samples.alias
    param_modified = UpdateIncludedSamples.modified_at.alias
    db_obj = await db.sample_group_collection.update_one(
        {GroupInfoDatabase.group_id.alias: group_id},
        {
            "$push": {
                param_included_sample: sample_obj.id,
                param_modified: datetime.now(),
            },
        },
    )
    return db_obj
