"""Functions for performing CURD operations on sample collection."""
import logging
from datetime import datetime
from itertools import groupby
from typing import Any, Dict, List

from bson.objectid import ObjectId
from fastapi.encoders import jsonable_encoder
from prp.models import PipelineResult
from prp.models.phenotype import AnnotationType, ElementType, PhenotypeInfo
from prp.models.tags import TagList

from ..crud.location import get_location
from ..crud.tags import compute_phenotype_tags
from ..db import Database
from ..models.antibiotics import ANTIBIOTICS
from ..models.base import RWModel
from ..models.location import LocationOutputDatabase
from ..models.qc import QcClassification, VariantAnnotation
from ..models.sample import (Comment, CommentInDatabase, SampleInCreate,
                             SampleInDatabase, SampleSummary)
from ..redis.minhash import (schedule_remove_genome_signature,
                             schedule_remove_genome_signature_from_index)
from ..utils import format_error_message
from .errors import EntryNotFound, UpdateDocumentError

LOG = logging.getLogger(__name__)
CURRENT_SCHEMA_VERSION = 1


class TypingProfileAggregate(RWModel):  # pylint: disable=too-few-public-methods
    """Sample id and predicted alleles."""

    sample_id: str
    typing_result: Dict[str, Any]

    def allele_profile(self, strip_errors: bool = True):
        """Get allele profile."""
        profile = {}
        for gene, allele in self.typing_result.items():
            if isinstance(allele, int):
                profile[gene] = allele
            elif isinstance(allele, str) and allele.startswith("*"):
                profile[gene] = int(allele[1:])
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
) -> List[SampleSummary]:
    """Get a summay of several samples."""
    # build query pipeline
    pipeline = []
    if include is not None:
        pipeline.append({"$match": {"sample_id": {"$in": include}}})
    if skip > 0:
        pipeline.append({"$skip": skip})
    if limit > 0:
        pipeline.append({"$limit": limit})

    pipeline.append(
        {
            "$addFields": {
                "typing_result": {
                    "$filter": {
                        "input": "$typing_result",
                        "as": "res",
                        "cond": {"$eq": ["$$res.type", "mlst"]},
                    }
                }
            }
        }
    )
    base_projection = {
        "_id": 0,
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
        optional_projecton["qc_status"] = 1
    if include_mlst:
        optional_projecton["mlst"] = {"$arrayElemAt": ["$typing_result", 0]}
    # add projections to pipeline
    pipeline.append({"$project": {**base_projection, **optional_projecton}})

    # query database
    cursor = db.sample_collection.aggregate(pipeline)
    # get query results from the database
    results = await cursor.to_list(None)

    if include_mlst:
        # replace mlst with the nested result as a work around
        # for mongo version < 5
        upd_results = []
        for res in results:
            if "mlst" in res:
                res["mlst"] = res["mlst"]["result"]
            upd_results.append(res)
        results = upd_results.copy()
    return results


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
        tags: TagList = compute_phenotype_tags(sample)
        sample.tags = tags
        if include is not None and sample.sample_id not in include:
            continue
        samp_objs.append(sample)
    return samp_objs


async def create_sample(db: Database, sample: PipelineResult) -> SampleInDatabase:
    """Create a new sample document in database from structured input."""
    # validate data format
    sample_db_fmt = SampleInCreate(
        in_collections=[],
        tags=compute_phenotype_tags(sample),
        **sample.model_dump(),
    )
    # store data in database
    doc = await db.sample_collection.insert_one(
        jsonable_encoder(sample_db_fmt, by_alias=False)
    )

    # create object representing the dataformat in database
    inserted_id = doc.inserted_id
    db_obj = SampleInDatabase(
        id=str(inserted_id),
        **sample_db_fmt.model_dump(),
    )
    return db_obj


async def update_sample(db: Database, updated_data: SampleInCreate) -> bool:
    """Replace an existing sample in the database with an updated version."""
    sample_id = updated_data.sample_id
    LOG.debug("Updating sample: %s in database", sample_id)

    # store data in database
    try:
        doc = await db.sample_collection.replace_one(
            {"sample_id": sample_id}, jsonable_encoder(updated_data, by_alias=False)
        )
    except Exception as err:
        LOG.error(
            "Error when updating sample: %s{sample_id} - %s",
            sample_id,
            format_error_message(err),
        )
        raise err

    # verify that only one sample found and one document was modified
    is_updated = doc.matched_count == 1 and doc.modified_count == 1
    return is_updated


async def delete_samples(db: Database, sample_ids: List[str]) -> bool:
    """Delete a sample from the database, remove it from groups, and remove its signature."""

    result = {
        "sample_ids": sample_ids,
        "n_deleted": 0,
        "removed_from_n_groups": 0,
        "remove_signature_jobs": None,
        "update_index_job": None,
    }
    # remove sample from database
    resp = await db.sample_collection.delete_many({"sample_id": {"$in": sample_ids}})
    # verify that only one sample found and one document was modified
    result["n_deleted"] = resp.deleted_count
    all_deleted = resp.deleted_count == len(sample_ids)
    LOG.info("Removing samples: %s; status: %s", ", ".join(sample_ids), all_deleted)

    # remove sample from group if sample was deleted
    resp = await db.sample_group_collection.update_many(
        {"included_samples": {"$in": sample_ids}},  # filter
        {
            "$pull": {
                "included_samples": {"$in": sample_ids}
            },  # remove samples from group
            "$set": {"modified_at": datetime.now()},  # update modified at
        },
    )
    # verify that number of modified groups and samples match
    result["removed_from_n_groups"] = resp.modified_count
    LOG.info(
        "Removing sample %s from groups; in n groups: %d; n modified documents: %d",
        ", ".join(sample_ids),
        resp.matched_count,
        resp.modified_count,
    )

    # remove signature from database and reindex database
    if result["n_deleted"] > 0:
        # remove signatures
        job_ids = []
        for sample_id in sample_ids:
            submitted_job = schedule_remove_genome_signature(sample_id)
            job_ids.append(submitted_job.id)
        result["remove_signature_jobs"] = job_ids
        # remove reindex
        index_job = schedule_remove_genome_signature_from_index(
            sample_ids, depends_on=job_ids
        )
        result["update_index_job"] = index_job.id
    return result


async def get_sample(db: Database, sample_id: str) -> SampleInDatabase:
    """Get sample with sample_id."""
    db_obj: SampleInDatabase = await db.sample_collection.find_one(
        {"sample_id": sample_id}
    )

    if db_obj is None:
        raise EntryNotFound(f"Sample {sample_id} not in database")

    inserted_id = db_obj["_id"]
    sample_obj = SampleInDatabase(
        **db_obj,
    )
    return sample_obj


async def add_comment(
    db: Database, sample_id: str, comment: Comment
) -> List[CommentInDatabase]:
    """Add comment to previously added sample."""
    # get existing comments for sample to get the next comment id
    sample = await get_sample(db, sample_id)
    comment_id = (
        max(c.id for c in sample.comments) + 1 if len(sample.comments) > 0 else 1
    )
    comment_obj = CommentInDatabase(id=comment_id, **comment.model_dump())
    update_obj = await db.sample_collection.update_one(
        {"sample_id": sample_id},
        {
            "$set": {"modified_at": datetime.now()},
            "$push": {
                "comments": {
                    "$each": [jsonable_encoder(comment_obj, by_alias=False)],
                    "$position": 0,
                }
            },
        },
    )

    if not update_obj.matched_count == 1:
        raise EntryNotFound(sample_id)
    if not update_obj.modified_count == 1:
        raise UpdateDocumentError(sample_id)
    LOG.info("Added comment to %s", sample_id)
    return [comment_obj.model_dump()] + sample.comments


async def hide_comment(db: Database, sample_id: str, comment_id: int) -> bool:
    """Add comment to previously added sample."""
    # get existing comments for sample to get the next comment id
    update_obj = await db.sample_collection.update_one(
        {"sample_id": sample_id, "comments.id": comment_id},
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
    LOG.info("Hide comment %s for %s", comment_id, sample_id)
    # update comments in return object
    return True


async def update_sample_qc_classification(
    db: Database, sample_id: str, classification: QcClassification
) -> bool:
    """Update the quality control classification of a sample"""

    query = {"sample_id": sample_id}
    update_obj = await db.sample_collection.update_one(
        query,
        {
            "$set": {
                "modified_at": datetime.now(),
                "qc_status": jsonable_encoder(classification, by_alias=False),
            }
        },
    )
    # verify successful update
    # if sample is not fund
    if not update_obj.matched_count == 1:
        raise EntryNotFound(sample_id)
    # if not modifed
    if not update_obj.modified_count == 1:
        raise UpdateDocumentError(sample_id)
    return classification


def update_variant_verificaton(variant, info):
    # update variant with selected annotations
    if info.verified is not None:
        LOG.debug("cals: %s", info)
        variant = variant.model_copy(
            update={"verified": info.verified, "reason": info.reason}
        )
    return variant


def update_variant_phenotype(variant, info, username):
    # update variant with selected annotations
    predicted_pheno = [
        phe
        for phe in variant.phenotypes
        if phe.annotation_type == AnnotationType.TOOL.value
    ]
    LOG.error(variant.phenotypes)
    if info.phenotypes is not None:
        annotated_pheno = []
        antibiotics_lookup = {ant.name: ant for ant in ANTIBIOTICS}
        for phenotype in info.phenotypes:
            # uppdate phenotypic annotation
            if phenotype in antibiotics_lookup:
                pheno = PhenotypeInfo(
                    name=phenotype,
                    group=antibiotics_lookup[phenotype].family,
                    type=ElementType.AMR,
                    annotation_type=AnnotationType.USER,
                    annotation_author=username,
                )
            else:
                pheno = PhenotypeInfo(
                    name=phenotype,
                    group="",
                    type=ElementType.AMR,
                    annotation_type=AnnotationType.USER,
                    annotation_author=username,
                )
            LOG.error(pheno)
            annotated_pheno.append(pheno)
        # update variant info
        variant = variant.model_copy(
            update={
                "phenotypes": predicted_pheno + annotated_pheno,
            }
        )
    return variant


async def update_variant_annotation_for_sample(
    db: Database, sample_id: str, classification: VariantAnnotation, username: str
) -> SampleInDatabase:
    """Update annotations of variants for a sample."""
    sample_info = await get_sample(db=db, sample_id=sample_id)
    # create variant group lookup table
    variant_id_gr = {
        gr_name: [int(id.split("-")[1]) for id in ids]
        for gr_name, ids in groupby(
            classification.variant_ids, key=lambda variant: variant.split("-")[0]
        )
    }
    # update element type results
    upd_results = []
    for pred_res in sample_info.element_type_result:
        # just store results that are not modified
        LOG.debug(
            "sw: %s; gr_sw: %s; sw not in gr ? %s",
            pred_res.software.value,
            list(variant_id_gr),
            pred_res.software.value not in variant_id_gr,
        )
        if pred_res.software.value not in variant_id_gr:
            upd_results.append(pred_res)
            continue
        # update individual variants
        upd_variants = []
        for variant in pred_res.result.variants:
            # update varaint if its id is in the list
            if variant.id in variant_id_gr[pred_res.software.value]:
                variant = update_variant_verificaton(variant, classification)
                variant = update_variant_phenotype(variant, classification, username)
            upd_variants.append(variant)

        # update prediction and add to list of updated results
        upd_results.append(
            pred_res.model_copy(
                update={
                    "result": pred_res.result.model_copy(
                        update={"variants": upd_variants}
                    )
                }
            )
        )
    updated_data = {"element_type_result": upd_results}
    # update SV variants
    for variant_type in ["snv_variants", "sv_variants"]:
        if variant_type in variant_id_gr:
            upd_variants = []
            for variant in getattr(sample_info, variant_type):
                if variant.id in variant_id_gr[variant_type]:
                    # update variant classification and annotation
                    LOG.error(
                        "CLS: %s; Variant before update: %s", classification, variant
                    )
                    variant = update_variant_verificaton(variant, classification)
                    variant = update_variant_phenotype(
                        variant, classification, username
                    )
                    LOG.error("Variant after update: %s", variant)
                upd_variants.append(variant)
            updated_data[variant_type] = upd_variants

    # update phenotypic prediction information in the database
    update_obj = await db.sample_collection.update_one(
        {"sample_id": sample_id},
        {
            "$set": {
                "modified_at": datetime.now(),
                **{
                    key: jsonable_encoder(value, by_alias=False)
                    for key, value in updated_data.items()
                },
            }
        },
    )
    # verify successful update
    # if sample is not fund
    if not update_obj.matched_count == 1:
        raise EntryNotFound(sample_id)
    # if not modifed
    if not update_obj.modified_count == 1:
        raise UpdateDocumentError(sample_id)
    # make a copy of updated result and return it
    upd_sample_info = sample_info.model_copy(update=updated_data)
    return upd_sample_info


async def add_location(
    db: Database, sample_id: str, location_id: str
) -> LocationOutputDatabase:
    """Add comment to previously added sample."""
    # Check if loaction is already in database
    try:
        location_obj = await get_location(db, location_id)
    except EntryNotFound as err:
        LOG.warning(
            "Tried to add location: %s to sample %s, location not found",
            location_id,
            sample_id,
        )
        raise err

    # Add location to samples
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
    LOG.info("Added location %s to %s", location_obj.display_name, sample_id)
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
        sample_ids = ", ".join(list(missing_samples))
        msg = f'The samples "{sample_ids}" didnt have {typing_method} typing result.'
        raise EntryNotFound(msg)
    return results


async def get_signature_path_for_samples(
    db: Database, sample_ids: list[str]
) -> TypingProfileOutput:
    """Get genome signature paths for samples."""
    LOG.info("Get signatures for samples")
    query = {
        "$and": [  # query for documents with
            {"sample_id": {"$in": sample_ids}},  # matching sample ids
            {"genome_signature": {"$ne": None}},  # AND genome_signatures not null
        ]
    }
    projection = {"_id": 0, "sample_id": 1, "genome_signature": 1}  # projection
    LOG.debug("Query: %s; projection: %s", query, projection)
    cursor = db.sample_collection.find(query, projection)
    results = await cursor.to_list(None)
    LOG.debug("Found %d signatures", len(results))
    return results
