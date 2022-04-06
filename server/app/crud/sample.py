"""Functions for performing CURD operations on sample collection."""
import logging
from datetime import datetime
from typing import Any, Dict, List

from bson.objectid import ObjectId

from ..crud.location import get_location
from ..db import Database
from ..models.location import LocationOutputDatabase
from ..models.sample import (Comment, CommentInDatabase ,SampleInCreate, SampleInDatabase,
                             SampleInPipelineInput)
from .errors import EntryNotFound, UpdateDocumentError

LOG = logging.getLogger(__name__)
CURRENT_SCHEMA_VERSION = 1


async def get_samples(db: Database, limit: int = 0, skip: int = 0) -> List[SampleInDatabase]:
    """Get locations from database."""

    cursor = db.sample_collection.find(limit=limit, skip=skip)
    samp_objs = []
    for samp in await cursor.to_list(None):
        inserted_id = samp["_id"]
        samp_objs.append(
            SampleInDatabase(
                id=str(inserted_id),
                created_at=ObjectId(inserted_id).generation_time,
                **samp,
            )
        )
    return samp_objs


async def create_sample(
    db: Database, sample: SampleInPipelineInput
) -> SampleInDatabase:
    """Create a new sample document in database from structured input."""
    # restructure data to db format

    # validate data format
    sample_db_fmt: SampleInCreate = SampleInCreate(
        sample_id=sample.sample_id,
        schema_version=CURRENT_SCHEMA_VERSION,
        in_collections=[],
        run_metadata=sample.run_metadata,
        qc=sample.qc,
        species_prediction=sample.species_prediction,
        add_typing_result=[
            {"type": "cgmlst", "result": sample.mlst},
            {"type": "cgmlst", "result": sample.cgmlst},
        ],
        add_phenotype_prediction=[
            {
                "type": "antimicrobial_resistance",
                "result": sample.antimicrobial_resistance,
            },
            {"type": "chemical_resistance", "result": sample.chemical_resistance},
            {
                "type": "environmental_factor_resistance",
                "result": sample.environmental_resistance,
            },
            {"type": "virulence", "result": sample.virulence},
        ],
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


async def add_comment(db: Database, sample_id: str, comment: Comment) -> List[CommentInDatabase]:
    """Add comment to previously added sample."""
    fields = SampleInDatabase.__fields__
    param_modified = fields["modified_at"].alias
    param_comment = fields["comments"].alias
    # get existing comments for sample to get the next comment id
    sample = await get_sample(db, sample_id)
    comment_id = max(c.id for c in sample.comments) + 1 if len(sample.comments) > 0 else 1
    comment_obj = CommentInDatabase(id=comment_id, **comment.dict())
    update_obj = await db.sample_collection.update_one(
        {fields["sample_id"].alias: sample_id},
        {
            "$set": {param_modified: datetime.now()},
            "$push": {param_comment: {
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


async def add_location(
    db: Database, sample_id: str, location_id: str
) -> LocationOutputDatabase:
    """Add comment to previously added sample."""
    # Check if loaction is already in database
    try:
        location_obj = await get_location(db, location_id)
    except EntryNotFound as err:
        LOG.warning(
            "Tried to add location: {location_id} to sample {sample_id}, location not found"
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
