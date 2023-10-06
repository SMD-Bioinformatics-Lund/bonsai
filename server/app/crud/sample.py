"""Functions for performing CURD operations on sample collection."""
import logging
from datetime import datetime
from typing import List
import sourmash
from pathlib import Path

from bson.objectid import ObjectId

from ..crud.location import get_location
from ..crud.tags import compute_phenotype_tags
from ..db import Database
from ..models.location import LocationOutputDatabase
from ..models.sample import (
    Comment,
    CommentInDatabase,
    SampleInCreate,
    SampleInDatabase,
    PipelineResult,
)
from ..models.sample import SampleInDatabase
from ..models.qc import QcClassification
from ..models.typing import CGMLST_ALLELES
from ..models.base import RWModel
from .errors import EntryNotFound, UpdateDocumentError
from app import config
import gzip
import pathlib
from ..utils import format_error_message
from fastapi.encoders import jsonable_encoder

LOG = logging.getLogger(__name__)
CURRENT_SCHEMA_VERSION = 1


class TypingProfileAggregate(RWModel):
    """Sample id and predicted alleles."""

    sample_id: str
    typing_result: CGMLST_ALLELES

    def allele_profile(self, strip_errors: bool = True):
        """Get allele profile."""
        profile = {}
        for gene, allele in self.typing_result.items():
            if isinstance(allele, int):
                profile[gene] = allele
            elif strip_errors:
                profile[gene] = None
            else:
                profile[gene] = allele
        return profile


TypingProfileOutput = list[TypingProfileAggregate]


async def get_samples_summary(
    db: Database,
    limit: int = 0,
    skip: int = 0,
    include: List[str] | None = None,
    include_qc: bool = True,
    include_mlst: bool = True,
    include_cgmlst: bool = True,
    include_amr: bool = True,
    include_virulence: bool = True,
) -> List[SampleInDatabase]:
    """Get a summay of several samples."""
    # build query pipeline
    pipeline = []
    if include is not None:
        pipeline.append({"$match": {"sample_id": {"$in": include}}})
    if skip > 0:
        pipeline.append({"$skip": skip})
    if limit > 0:
        pipeline.append({"$limit": limit})


    pipeline.append({
        "$addFields": {
            "typing_result": {
                "$filter": {
                    "input": "$typing_result",
                    "as": "res",
                    "cond": {"$eq": ["$$res.type", "mlst"]}
                }
            }
        }
    })
    base_projection = {"_id": 0, 
                       "id": {"$convert": {"input": "$_id", "to": "string"}}, 
                       "sample_id": 1, 
                       "tags": 1, 
                       "species_prediction": {"$arrayElemAt": ["$species_prediction", 0]},
                       "created_at": 1, 
                       "profile": "$run_metadata.run.analysis_profile",
                       }
    # define a optional projections
    optional_projecton = {}
    if include_qc:
        optional_projecton["qc_status"] = int(include_qc),
    if include_mlst:
        optional_projecton["mlst"] = {"$getField": {"field": "result", "input": {"$arrayElemAt": ["$typing_result", 0]}}},
    # add projections to pipeline
    pipeline.append({"$project": {**base_projection, **optional_projecton}})

    # query database
    cursor = db.sample_collection.aggregate(pipeline)
    return await cursor.to_list(None)


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
        # Compute tags
        tags: TAG_LIST = compute_phenotype_tags(sample)
        sample.tags = tags
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
    doc = await db.sample_collection.insert_one(jsonable_encoder(sample_db_fmt))
    # print(sample_db_fmt.dict(by_alias=True))

    # create object representing the dataformat in database
    inserted_id = doc.inserted_id
    db_obj = SampleInDatabase(
        id=str(inserted_id),
        **sample_db_fmt.dict(),
    )
    return db_obj


async def update_sample(db: Database, updated_data: SampleInCreate) -> bool:
    """Replace an existing sample in the database with an updated version."""
    sample_id = updated_data.sample_id
    LOG.debug(f"Updating sample: {sample_id} in database")

    # store data in database
    try:
        doc = await db.sample_collection.replace_one(
            {"sample_id": sample_id}, updated_data.dict()
        )
    except Exception as err:
        LOG.error(
            f"Error when updating sample: {sample_id} - {format_error_message(err)}"
        )
        raise err

    # verify that only one sample found and one document was modified
    is_updated = doc.matched_count == 1 and doc.modified_count == 1
    return is_updated


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
    # Compute tags
    tags: TAG_LIST = compute_phenotype_tags(sample_obj)
    sample_obj.tags = tags
    return sample_obj


async def add_comment(
    db: Database, sample_id: str, comment: Comment
) -> List[CommentInDatabase]:
    """Add comment to previously added sample."""
    fields = SampleInDatabase.__fields__
    # get existing comments for sample to get the next comment id
    sample = await get_sample(db, sample_id)
    comment_id = (
        max(c.id for c in sample.comments) + 1 if len(sample.comments) > 0 else 1
    )
    comment_obj = CommentInDatabase(id=comment_id, **comment.dict())
    update_obj = await db.sample_collection.update_one(
        {"sample_id": sample_id},
        {
            "$set": {"modified_at": datetime.now()},
            "$push": {
                "comments": {
                    "$each": [jsonable_encoder(comment_obj)],
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
    # get existing comments for sample to get the next comment id
    update_obj = await db.sample_collection.update_one(
        {"sample_id": sample_id, f"{param_comment}.id": comment_id},
        {
            "$set": {
                "modified_at": datetime.now(),
                "comments.$.displayed": False,
            },
        },
    )
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


async def update_sample_qc_classification(db: Database, sample_id: str, classification: QcClassification) -> bool:
    """Update the quality control classification of a sample"""

    query = {"sample_id": sample_id}
    update_obj = await db.sample_collection.update_one(query, {
        "$set": {
            "modified_at": datetime.now(),
            "qc_status": jsonable_encoder(classification)
        }
    })
    # verify successful update
    # if sample is not fund
    if not update_obj.matched_count == 1:
        raise EntryNotFound(sample_id)
    # if not modifed
    if not update_obj.modified_count == 1:
        raise UpdateDocumentError(sample_id)
    return classification


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
    update_obj = await db.sample_collection.update_one(
        {"sample_id": sample_id},
        {
            "$set": {
                "modified_at": datetime.now(),
                "location": ObjectId(location_id),
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
    missing_samples = set(sample_idx) - {s.sample_id for s in results}
    if len(missing_samples) > 0:
        msg = 'The samples "%s" didnt have %s typing result.' % (
            ", ".join(list(missing_samples)),
            typing_method,
        )
        raise EntryNotFound(msg)
    return results


def get_samples_similar_to_reference(
    sample_id: str, min_similarity: float, kmer_size: int, limit: int | None = None
):
    """Get find samples that are similar to reference sample.

    min_similarity - minimum similarity score to be included

    """

    # load sourmash index
    signature_dir = Path(config.GENOME_SIGNATURE_DIR)
    index_path = signature_dir.joinpath(f"genomes.sbt.zip")
    # ensure that index exist
    if not index_path.is_file():
        raise FileNotFoundError(f"Sourmash index does not exist: {index_path}")
    tree = sourmash.load_file_as_index(str(index_path))

    # load reference sequence
    query_signature_path = signature_dir.joinpath(f"{sample_id}.sig")
    if not query_signature_path.is_file():
        raise FileNotFoundError(f"Signature file not found, {query_signature_path}")
    query_signature = list(sourmash.load_file_as_signatures(
        str(query_signature_path), ksize=kmer_size
    ))
    if len(query_signature) == 0:
        raise ValueError(f'No signature in: {sample_id} with kmer size: {kmer_size}')
    else:
        query_signature = query_signature[0]

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
        base_fname = hit_fname.name[: -len(hit_fname.suffix)]
        samples.append({"sample_id": base_fname, "similarity": similarity})
    return samples


def add_genome_signature_to_index(signature_file: pathlib.Path) -> bool:
    """Add genome signature file to sourmash index"""
    signature = next(
        sourmash.load_file_as_signatures(
            str(signature_file.resolve()), ksize=config.SIGNATURE_KMER_SIZE
        )
    )

    # get signature directory
    signature_db = pathlib.Path(config.GENOME_SIGNATURE_DIR)

    # add signature to existing index
    sbt_filename = signature_db.joinpath("genomes.sbt.zip")
    if sbt_filename.is_file():
        LOG.debug("Append to existing file")
        tree = sourmash.load_file_as_index(str(sbt_filename.resolve()))
    else:
        LOG.debug("Create new index file")
        tree = sourmash.sbtmh.create_sbt_index()
    # add generated signature to bloom tree
    LOG.info("Adding genome signatures to index")
    leaf = sourmash.sbtmh.SigLeaf(signature.md5sum(), signature)
    tree.add_node(leaf)
    # save updated bloom tree
    try:
        tree.save(str(sbt_filename))
    except PermissionError as err:
        LOG.error("Dont have permission to write file to disk")
        raise err

    return True


def add_genome_signature_file(sample_id: str, signature) -> pathlib.Path:
    """
    Add new genome signature file to host file system.

    and create or update existing index if required.
    """
    # get signature directory
    signature_db = pathlib.Path(config.GENOME_SIGNATURE_DIR)
    # make db if signature db is not present
    if not signature_db.exists():
        signature_db.mkdir(parents=True, exist_ok=True)

    # check that signature doesnt exist
    signature_file = signature_db.joinpath(f"{sample_id}.sig")
    if signature_file.is_file():
        raise FileExistsError("Signature file already exists")

    # check if compressed and decompress data
    if signature[:2] == b"\x1f\x8b":
        LOG.debug("Decompressing gziped file")
        signature = gzip.decompress(signature)

    # save signature to file
    LOG.info("Writing genome signatures to file")
    try:
        with open(signature_file, "w") as out:
            print(signature.decode("utf-8"), file=out)
    except PermissionError as err:
        LOG.error(f"Dont have permission to write file to disk - {', '.join(err.args)}")
        raise err

    # add signature to index
    try:
        add_genome_signature_to_index(signature_file)
    except Exception as err:
        # remove signature file from disk in case of errors
        LOG.debug("Error encounterd when appending signature, removing signature file")
        signature_file.unlink()
        raise err

    return signature_file


def remove_genome_signature_file(sample_id: str) -> bool:
    """Remove an existing signature file from disk."""

    # get signature directory
    signature_db = pathlib.Path(config.GENOME_SIGNATURE_DIR)

    # check that signature doesnt exist
    signature_file = signature_db.joinpath(f"{sample_id}.sig")
    if signature_file.is_file():
        # load signature to memory
        signature = next(
            sourmash.signature.load_signatures(
                signature_file, ksize=config.SIGNATURE_KMER_SIZE
            )
        )
        # remove file
        signature_file.unlink()
    else:
        raise FileNotFoundError(f"Signature file: {signature_file} not found")

    # remove signature to existing index
    sbt_filename = signature_db.joinpath("genomes.sbt.zip")
    if sbt_filename.is_file():
        LOG.debug("Append to existing file")
        tree = sourmash.load_file_as_index(str(sbt_filename))

        # add generated signature to bloom tree
        LOG.info("Adding genome signatures to index")
        leaf = sourmash.sbtmh.SigLeaf(signature.md5sum(), signature)
        tree.remove_many(leaf)

        try:
            tree.save(str(sbt_filename.resolve()))
        except PermissionError as err:
            LOG.error("Dont have permission to write file to disk")
            raise err
        return True
    LOG.info(f"Signature file: {signature_file} was removed")
    return False
