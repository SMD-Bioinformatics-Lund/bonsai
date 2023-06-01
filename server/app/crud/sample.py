"""Functions for performing CURD operations on sample collection."""
import logging
from datetime import datetime
from typing import List
import sourmash
from pathlib import Path

from bson.objectid import ObjectId

from ..crud.location import get_location
from ..db import Database
from ..models.location import LocationOutputDatabase
from ..models.sample import (
    Comment,
    CommentInDatabase,
    SampleInCreate,
    SampleInDatabase,
    PipelineResult,
)
from ..models.typing import CGMLST_ALLELES
from ..models.base import RWModel
from .errors import EntryNotFound, UpdateDocumentError
from app import config

LOG = logging.getLogger(__name__)
CURRENT_SCHEMA_VERSION = 1


class TypingProfileAggregate(RWModel):
    """Sample id and predicted alleles."""

    sampleId: str
    typingResult: CGMLST_ALLELES


TypingProfileOutput = list[TypingProfileAggregate]


async def get_samples(
    db: Database,
    limit: int = 0,
    skip: int = 0,
    include: List[str] | None = None,
) -> List[SampleInDatabase]:
    """Get samples from database."""

    cursor = db.sample_collection.find(limit=limit, skip=skip)
    samp_objs = []
    for samp in await cursor.to_list(None):
        inserted_id = samp["_id"]
        sample = SampleInDatabase(
            id=str(inserted_id),
            **samp,
        )
        # TODO replace with aggregation pipeline
        if include is not None and sample.sample_id not in include:
            continue
        samp_objs.append(sample)
    return samp_objs


async def create_sample(db: Database, sample: PipelineResult) -> SampleInDatabase:
    """Create a new sample document in database from structured input."""
    # validate data format
    sample_db_fmt: SampleDatabaseInput = SampleInCreate(
        in_collections=[], **sample.dict()
    )
    # store data in database
    doc = await db.sample_collection.insert_one(sample_db_fmt.dict())
    # print(sample_db_fmt.dict(by_alias=True))

    # create object representing the dataformat in database
    inserted_id = doc.inserted_id
    db_obj = SampleInDatabase(
        id=str(inserted_id),
        **sample_db_fmt.dict(),
    )
    return db_obj


async def get_sample(db: Database, sample_id: str) -> SampleInDatabase:
    """Get sample with sample_id."""
    db_obj: SampleInCreate = await db.sample_collection.find_one(
        {"sample_id": sample_id}
    )

    if db_obj is None:
        raise EntryNotFound(f"Sample {sample_id} not in database")

    inserted_id = db_obj["_id"]
    sample_obj = SampleInDatabase(
        id=str(inserted_id),
        **db_obj,
    )
    return sample_obj


async def add_comment(
    db: Database, sample_id: str, comment: Comment
) -> List[CommentInDatabase]:
    """Add comment to previously added sample."""
    fields = SampleInDatabase.__fields__
    param_modified = fields["modified_at"]
    param_comment = fields["comments"]
    # get existing comments for sample to get the next comment id
    sample = await get_sample(db, sample_id)
    comment_id = (
        max(c.id for c in sample.comments) + 1 if len(sample.comments) > 0 else 1
    )
    comment_obj = CommentInDatabase(id=comment_id, **comment.dict())
    update_obj = await db.sample_collection.update_one(
        {fields["sample_id"]: sample_id},
        {
            "$set": {param_modified: datetime.now()},
            "$push": {
                param_comment: {
                    "$each": [comment_obj.dict()],
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
    param_modified = fields["modified_at"]
    param_comment = fields["comments"]
    # get existing comments for sample to get the next comment id
    print([param_comment, sample_id, comment_id])
    update_obj = await db.sample_collection.update_one(
        {fields["sample_id"]: sample_id, f"{param_comment}.id": comment_id},
        {
            "$set": {
                param_modified: datetime.now(),
                f"{param_comment}.$.displayed": False,
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
    param_modified = fields["modified_at"]
    param_location = fields["location"]
    update_obj = await db.sample_collection.update_one(
        {fields["sample_id"]: sample_id},
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


async def get_typing_profiles(
    db: Database, sample_idx: list[str], typing_method: str
) -> TypingProfileOutput:
    """Get locations from database."""
    pipeline = [
        {"$project": {"_id": 0, "sample_id": 1, "typing_result": 1}},
        {"$unwind": "$typing_result"},
        {
            "$match": {
                "$and": [
                    {"sample_id": {"$in": sample_idx}},
                    {"typing_result.type": typing_method},
                ]
            }
        },
        {"$addFields": {"typing_result": "$typing_result.result.alleles"}},
    ]

    # query database
    results = [
        TypingProfileAggregate(**sample)
        async for sample in db.sample_collection.aggregate(pipeline)
    ]
    missing_samples = set(sample_idx) - {s.sampleId for s in results}
    if len(missing_samples) > 0:
        msg = 'The samples "%s" didnt have %s typing result.' % (
            ", ".join(list(missing_samples)),
            typing_method,
        )
        raise EntryNotFound(msg)
    return results


def get_samples_similar_to_reference(sample_id: str, min_similarity: float, kmer_size: int = 21, limit: int | None = None):
    """Get find samples that are similar to reference sample.
    
    min_similarity - minimum similarity score to be included
    
    """

    # load sourmash index
    signature_dir = Path(config.GENOME_SIGNATURE_DIR)
    index_path = signature_dir.joinpath(f"samples.sbt.zip")
    # ensure that index exist
    if not index_path.is_file():
        raise FileNotFoundError(f'Sourmash index does not exist: {index_path}')
    tree = sourmash.load_file_as_index(str(index_path))

    # load reference sequence
    query_signature_path = signature_dir.joinpath('samples', f"{sample_id}.sig")
    if not query_signature_path.is_file():
        raise FileNotFoundError(f"Signature file not found, {query_signature_path}")
    query_signature = sourmash.load_one_signature(
            str(query_signature_path), ksize=kmer_size
    )

    # query for similar sequences
    result = tree.search(query_signature, threshold=min_similarity)
    
    # read sample information of similar samples
    samples = []
    for itr_no, (similarity, found_sig, _) in enumerate(result):
        # limit the number of samples
        if limit and limit < itr_no:
            break
        # read sample results
        hit_fname = Path(found_sig.filename)
        # extract sample id from sample name
        base_fname = hit_fname.name[:-len(hit_fname.suffix)]
        samples.append({'sample_id': base_fname, 'similarity': similarity})
    return samples