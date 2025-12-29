"""Functions for performing CURD operations on sample collection."""

import logging
from itertools import groupby
from typing import Any

import bonsai_api
from api_client.audit_log import AuditLogClient, EventCreate
from api_client.audit_log.models import SourceType, Subject
from bonsai_api.crud.location import get_location
from bonsai_api.crud.summary import get_samples_summary
from bonsai_api.crud.tags import compute_phenotype_tags
from bonsai_api.crud.utils import audit_event_context
from bonsai_api.db import Database
from bonsai_api.dependencies import ApiRequestContext
from bonsai_api.models.antibiotics import ANTIBIOTICS
from bonsai_api.models.base import MultipleRecordsResponseModel
from bonsai_api.models.location import LocationOutputDatabase
from bonsai_api.models.qc import QcClassification, VariantAnnotation
from bonsai_api.models.sample import (Comment, CommentInDatabase,
                                      SampleInCreate, SampleInDatabase)
from bonsai_api.redis.minhash import (
    schedule_remove_genome_signature,
    schedule_remove_genome_signature_from_index)
from bonsai_api.utils import format_error_message, get_timestamp
from bson.objectid import ObjectId
from fastapi.encoders import jsonable_encoder
from prp.models import PipelineResult
from prp.models.phenotype import AnnotationType, ElementType, PhenotypeInfo
from pymongo import ASCENDING, DESCENDING
from pymongo.results import UpdateResult

from .errors import DatabaseOperationError, EntryNotFound

LOG = logging.getLogger(__name__)
CURRENT_SCHEMA_VERSION = 1


async def get_samples_full(
    db: Database,
    *,
    match: dict[str, Any],
    fields: list[str] | None,
    sort: str,
    limit: int,
    offset: int | None,
) -> MultipleRecordsResponseModel:
    """Get full sample info with optional projections."""
    allowed_fields = {
        "sample_id": 1,
        "sample_name": 1,
        "metadata": 1,
        "groups": 1,
        "species_prediction": 1,
        "pipeline": 1,
        "tags": 1,
        "comments": 1,
        "created_at": 1,
        "lims_id": 1,
        "sequencing": 1,
        "qc_status": 1,
        "typing_results": 1,
        "element_type_results": 1,
    }

    # build an inclusion projection (1 for requested fields)
    projection: dict[str, int] = {"_id": 0}
    if fields:
        additonal_fields = {f: allowed_fields[f] for f in fields if f in allowed_fields}
        projection.update(additonal_fields)

    # Sort
    sort_dir = DESCENDING if sort.startswith("-") else ASCENDING
    sort_key = sort[1:] if sort.startswith("-") else sort
    allowed_sorts = {"created_at": "created_at", "_id": "_id", "sample_id": "sample_id"}
    if sort_key not in allowed_sorts:
        raise ValueError(f"Unsupported sort: {sort_key}")
    sort_tuple = [(allowed_sorts[sort_key], sort_dir), ("_id", sort_dir)]

    # Query
    cursor = db.sample_collection.find(match, projection).sort(sort_tuple)
    if offset and offset > 0:
        cursor = cursor.skip(offset)
    if limit and limit > 0:
        cursor = cursor.limit(limit)

    data = await cursor.to_list(None)
    total = await db.sample_collection.count_documents(match)
    return MultipleRecordsResponseModel(data=data, records_total=total)


async def create_sample(
    db: Database,
    sample: PipelineResult,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> SampleInDatabase:
    """Create a new sample document in database from structured input."""
    # validate data format
    try:
        tags = compute_phenotype_tags(sample)
    except ValueError as error:
        LOG.warning("Error when creating tags... skipping. %s", error)
        tags = []

    event_subject = Subject(id=sample.sample_id, type=SourceType.USR)
    with audit_event_context(audit, "create_sample", ctx, event_subject):
        sample_db_fmt = SampleInCreate(
            in_collections=[],
            tags=tags,
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


async def delete_samples(
    db: Database,
    sample_ids: list[str],
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> dict[str, Any]:
    """Delete a sample from the database, remove it from groups, and remove its signature."""
    result: dict[str, Any] = {
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
            "$set": {"modified_at": get_timestamp()},  # update modified at
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
    samples_was_removed = result["n_deleted"] > 0
    if samples_was_removed:
        # remove signatures
        job_ids: list[str] = []
        for sample_id in sample_ids:
            submitted_job = schedule_remove_genome_signature(sample_id)
            job_ids.append(submitted_job.id)
        result["remove_signature_jobs"] = job_ids
        # remove reindex
        index_job = schedule_remove_genome_signature_from_index(
            sample_ids, depends_on=job_ids
        )
        result["update_index_job"] = index_job.id

    if isinstance(audit, AuditLogClient) and samples_was_removed:
        for sample_id in sample_ids:
            # prepare event metadata and submit event
            event_subject = Subject(id=sample_id, type=SourceType.USR)
            event = EventCreate(
                source_service=bonsai_api.__name__,
                event_type="delete_sample",
                actor=ctx.actor,
                subject=event_subject,
                metadata=ctx.metadata,
            )
            audit.post_event(event)

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
    db: Database,
    sample_id: str,
    comment: Comment,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> list[CommentInDatabase]:
    """Add comment to previously added sample."""
    # get existing comments for sample to get the next comment id
    sample = await get_sample(db, sample_id)
    comments: list[CommentInDatabase] = sample.comments
    comment_id = (
        max(c.id for c in sample.comments) + 1 if len(sample.comments) > 0 else 1
    )
    event_subject = Subject(id=sample_id, type=SourceType.USR)
    meta = {"sample_id": sample_id, "comment_id": comment_id}
    with audit_event_context(audit, "create_comment", ctx, event_subject, meta):
        comment_obj = CommentInDatabase(id=comment_id, **comment.model_dump())
        update_obj: UpdateResult = await db.sample_collection.update_one(
            {"sample_id": sample_id},
            {
                "$set": {"modified_at": get_timestamp()},
                "$push": {
                    "comments": {
                        "$each": [comment_obj.model_dump(by_alias=False)],
                        "$position": 0,
                    }
                },
            },
        )

        if not update_obj.matched_count == 1:
            raise EntryNotFound(sample_id)
        if not update_obj.modified_count == 1:
            raise DatabaseOperationError(sample_id)

        LOG.info("Added comment to %s", sample_id)
        comments.insert(0, comment_obj)
    return comments


async def hide_comment(
    db: Database,
    sample_id: str,
    comment_id: int,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> bool:
    """Add comment to previously added sample."""
    # get existing comments for sample to get the next comment id
    event_subject = Subject(id=sample_id, type=SourceType.USR)
    meta: dict[str, str | int] = {"sample_id": sample_id, "comment_id": comment_id}
    with audit_event_context(audit, "delete_comment", ctx, event_subject, meta):
        update_obj = await db.sample_collection.update_one(
            {"sample_id": sample_id, "comments.id": comment_id},
            {
                "$set": {
                    "modified_at": get_timestamp(),
                    "comments.$.displayed": False,
                },
            },
        )
        if not update_obj.matched_count == 1:
            raise EntryNotFound(sample_id)
        if not update_obj.modified_count == 1:
            raise DatabaseOperationError(sample_id)

        LOG.info("Hide comment %s for %s", comment_id, sample_id)
    return True


async def update_sample_qc_classification(
    db: Database,
    sample_id: str,
    classification: QcClassification,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> QcClassification:
    """Update the quality control classification of a sample"""

    query = {"sample_id": sample_id}
    event_subject = Subject(id=sample_id, type=SourceType.USR)
    with audit_event_context(audit, "update_qc", ctx, event_subject):
        update_obj: UpdateResult = await db.sample_collection.update_one(
            query,
            {
                "$set": {
                    "modified_at": get_timestamp(),
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
            raise DatabaseOperationError(sample_id)
    return classification


def update_variant_verificaton(variant, info):
    """Update variant with selected annotations."""

    if info.verified is not None:
        LOG.debug("cals: %s", info)
        variant = variant.model_copy(
            update={"verified": info.verified, "reason": info.reason}
        )
    return variant


def update_variant_phenotype(variant, info, username):
    """Update variant with selected annotations"""

    predicted_pheno = [
        phe
        for phe in variant.phenotypes
        if phe.annotation_type == AnnotationType.TOOL.value
    ]
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
                    resistance_level=info.resistance_lvl,
                    annotation_type=AnnotationType.USER,
                    annotation_author=username,
                )
            else:
                pheno = PhenotypeInfo(
                    name=phenotype,
                    group="",
                    type=ElementType.AMR,
                    resistance_level=info.resistance_lvl,
                    annotation_type=AnnotationType.USER,
                    annotation_author=username,
                )
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
    update_obj: UpdateResult = await db.sample_collection.update_one(
        {"sample_id": sample_id},
        {
            "$set": {
                "modified_at": get_timestamp(),
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
        raise DatabaseOperationError(sample_id)
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
    update_obj: UpdateResult = await db.sample_collection.update_one(
        {"sample_id": sample_id},
        {
            "$set": {
                "modified_at": get_timestamp(),
                "location": ObjectId(location_id),
            }
        },
    )
    if not update_obj.matched_count == 1:
        raise EntryNotFound(sample_id)
    if not update_obj.modified_count == 1:
        raise DatabaseOperationError(sample_id)
    LOG.info("Added location %s to %s", location_obj.display_name, sample_id)
    return location_obj
