"""Functions for performing CURD operations on sample collection."""
import logging
from datetime import datetime
from typing import List

from bson.objectid import ObjectId

from ..crud.location import get_location
from ..db import Database
from ..models.location import LocationOutputDatabase
from ..models.sample import (Comment, CommentInDatabase, SampleInCreate,
                             SampleInDatabase, PipelineResult)
from ..models.typing import CGMLST_ALLELES
from ..models.base import RWModel
from .errors import EntryNotFound, UpdateDocumentError

LOG = logging.getLogger(__name__)
CURRENT_SCHEMA_VERSION = 1

class TypingProfileAggregate(RWModel):
    """Sample id and predicted alleles."""

    sampleId: str
    typingResult: CGMLST_ALLELES

TypingProfileOutput = list[TypingProfileAggregate]


async def get_samples(
    db: Database, limit: int = 0, skip: int = 0, include: List[str] | None = None,
) -> List[SampleInDatabase]:
    """Get samples from database."""

    cursor = db.sample_collection.find(limit=limit, skip=skip)
    samp_objs = []
    for samp in await cursor.to_list(None):
        inserted_id = samp["_id"]
        sample = SampleInDatabase(
                id=str(inserted_id),
                created_at=ObjectId(inserted_id).generation_time,
                **samp,
            )
        # TODO replace with aggregation pipeline
        if include is not None and sample.sample_id not in include:
            continue
        samp_objs.append(sample)
    return samp_objs


async def create_sample(
    db: Database, sample: PipelineResult
) -> SampleInDatabase:
    """Create a new sample document in database from structured input."""
    # validate data format
    sample_db_fmt: SampleDatabaseInput = SampleInCreate(
        in_collections=[],
        **sample.dict()
    )
    # store data in database
    doc = await db.sample_collection.insert_one(sample_db_fmt.dict(by_alias=True))
    # print(sample_db_fmt.dict(by_alias=True))

    # create object representing the dataformat in database
    inserted_id = doc.inserted_id
    db_obj = SampleInDatabase(
        id=str(inserted_id),
        created_at=ObjectId(inserted_id).generation_time,
        modified_at=ObjectId(inserted_id).generation_time,
        **sample_db_fmt.dict(by_alias=True),
    )
    return db_obj


async def get_sample(db: Database, sample_id: str) -> SampleInDatabase:
    """Get sample with sample_id."""
    db_obj: SampleInCreate = await db.sample_collection.find_one(
        {"sampleId": sample_id}
    )

    if db_obj is None:
        raise EntryNotFound(f"Sample {sample_id} not in database")

    inserted_id = db_obj["_id"]
    sample_obj = SampleInDatabase(
        id=str(inserted_id),
        created_at=ObjectId(inserted_id).generation_time,
        modified_at=ObjectId(inserted_id).generation_time,
        **db_obj,
    )
    return sample_obj


async def add_comment(
    db: Database, sample_id: str, comment: Comment
) -> List[CommentInDatabase]:
    """Add comment to previously added sample."""
    fields = SampleInDatabase.__fields__
    param_modified = fields["modified_at"].alias
    param_comment = fields["comments"].alias
    # get existing comments for sample to get the next comment id
    sample = await get_sample(db, sample_id)
    comment_id = (
        max(c.id for c in sample.comments) + 1 if len(sample.comments) > 0 else 1
    )
    comment_obj = CommentInDatabase(id=comment_id, **comment.dict())
    update_obj = await db.sample_collection.update_one(
        {fields["sample_id"].alias: sample_id},
        {
            "$set": {param_modified: datetime.now()},
            "$push": {
                param_comment: {
                    "$each": [comment_obj.dict(by_alias=True)],
                    "$position": 0,
                }
            },
        },
    )
    if not update_obj.matched_count == 1:
        raise EntryNotFound(sample_id)
    if not update_obj.modified_count == 1:
        raise UpdateDocumentError(sample_id)
    LOG.info(f"Added comment to {sample_id}")
    return [comment_obj.dict()] + sample.comments


async def hide_comment(
    db: Database, sample_id: str, comment_id: int
) -> List[CommentInDatabase]:
    """Add comment to previously added sample."""
    fields = SampleInDatabase.__fields__
    param_modified = fields["modified_at"].alias
    param_comment = fields["comments"].alias
    # get existing comments for sample to get the next comment id
    print([param_comment, sample_id, comment_id])
    update_obj = await db.sample_collection.update_one(
        {fields["sample_id"].alias: sample_id, f"{param_comment}.id": comment_id},
        {
            "$set": {
                param_modified: datetime.now(), 
                f"{param_comment}.$.displayed": False
            }, 
        },
    )
    print([update_obj.matched_count, update_obj.modified_count])
    if not update_obj.matched_count == 1:
        raise EntryNotFound(sample_id)
    if not update_obj.modified_count == 1:
        raise UpdateDocumentError(sample_id)
    LOG.info(f"Hide comment {comment_id} for {sample_id}")
    # update comments in return object
    comments = []
    for cmt in comments:
        cmd.displayed = False if cmt.id == comment_id else cmt.displayed
        comments.append(cmt)
    return comments


async def add_location(
    db: Database, sample_id: str, location_id: str
) -> LocationOutputDatabase:
    """Add comment to previously added sample."""
    # Check if loaction is already in database
    try:
        location_obj = await get_location(db, location_id)
    except EntryNotFound as err:
        LOG.warning(
            f"Tried to add location: {location_id} to sample {sample_id}, location not found"
        )
        raise err

    # Add location to samples
    fields = SampleInDatabase.__fields__
    param_modified = fields["modified_at"].alias
    param_location = fields["location"].alias
    update_obj = await db.sample_collection.update_one(
        {fields["sample_id"].alias: sample_id},
        {
            "$set": {
                param_modified: datetime.now(),
                param_location: ObjectId(location_id),
            }
        },
    )
    if not update_obj.matched_count == 1:
        raise EntryNotFound(sample_id)
    if not update_obj.modified_count == 1:
        raise UpdateDocumentError(sample_id)
    LOG.info(f"Added location {location_obj.display_name} to {sample_id}")
    return location_obj


async def get_typing_profiles(db: Database, sample_idx: list[str], typing_method: str) -> TypingProfileOutput:
    """Get locations from database."""
    pipeline = [
        {"$project": {"_id": 0, "sampleId": 1, "typingResult": 1}},
        {"$unwind": "$typingResult"},
        {"$match": {"$and": [
            {"sampleId": {"$in": sample_idx}}, 
            {"typingResult.type": typing_method}
        ]}},
        {"$addFields": {"typingResult": "$typingResult.result.alleles"}}
    ]

    # query database
    results = [
        TypingProfileAggregate(**sample)
        async for sample 
        in db.sample_collection.aggregate(pipeline)
    ]
    missing_samples = set(sample_idx) - {s.sampleId for s in results}
    if len(missing_samples) > 0:
        msg = 'The samples "%s" didnt have %s typing result.' % (
            ", ".join(list(missing_samples)), typing_method
        )
        raise EntryNotFound(msg)
    return results