"""Functions for conducting CURD operations on group collection"""
import logging
from datetime import datetime
from multiprocessing.sharedctypes import Value
from random import sample
from typing import Any, Dict, List

from bson.objectid import ObjectId

from ..db import Database
from ..models.group import (GroupInCreate, GroupInfoDatabase,
                            UpdateIncludedSamples)
from ..models.sample import SampleSummary
from ..models.typing import TypingMethod
from ..models.tags import TAG_LIST
from .errors import EntryNotFound, UpdateDocumentError
from .sample import get_sample
from .tags import compute_phenotype_tags

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


async def get_group(db: Database, group_id: str, lookup_samples: bool = False) -> GroupInfoDatabase:
    """Get collections from database."""
    group_fields = GroupInfoDatabase.__fields__
    sample_fields = SampleSummary.__fields__
    included_samples_field = group_fields["included_samples"].alias

    # make aggregation pipeline
    pipeline = [
        {"$match": {group_fields["group_id"].alias: group_id}},
    ]
    if lookup_samples:
        typing_field = sample_fields["typing_result"].alias
        pipeline.extend([{
            "$lookup": {
                "from": db.sample_collection.name,
                "localField": included_samples_field,
                "foreignField": sample_fields["sample_id"].alias,
                "as": included_samples_field,
                "pipeline": [
                    {"$addFields": {
                        typing_field: {
                            "$filter": {
                                "input": f"${typing_field}",
                                "as": "result",
                                "cond": {"$ne": ["$$result.type", TypingMethod.CGMLST.value]},
                            }
                        },
                        sample_fields["major_specie"].alias: {"$first": f"${sample_fields['species_prediction'].alias}"}
                    }}
                ]
            }
        }])
    async for group in db.sample_group_collection.aggregate(pipeline):
        # compute tags for samples if samples are included
        if lookup_samples:
            for sample in group[included_samples_field]:
                # cast as static object
                tags: TAG_LIST = compute_phenotype_tags(SampleSummary(**sample))
                sample["tags"] = tags
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


async def append_sample_to_group(db: Database, sample_id: str, group_id: str) -> None:
    """Create a new collection document."""
    sample_obj = await get_sample(db, sample_id)
    fields = UpdateIncludedSamples.__fields__
    param_included_sample = fields["included_samples"].alias
    param_modified = fields["modified_at"].alias
    gid_filed = GroupInfoDatabase.__fields__["group_id"]
    update_obj = await db.sample_group_collection.update_one(
        {gid_filed.alias: group_id},
        {
            "$set": {param_modified: datetime.now()},
            "$addToSet": {
                param_included_sample: sample_obj.sample_id,
            },
        },
    )
    if not update_obj.matched_count == 1:
        raise EntryNotFound(group_id)
    if not update_obj.modified_count == 1:
        raise UpdateDocumentError(group_id)
