"""Service layer for creating and modifying sample info."""

import itertools
import logging
from typing import Any

from .genomic_resource_service import list_genomic_resources_for_sample_service
import uuid_utils as uuid
from api_client.audit_log.client import AuditLogClient
from api_client.audit_log.models import SourceType, Subject
from bonsai_api.crud.group import check_groups_exists
from bonsai_api.crud.sample import (
    add_pipeline_run,
    add_reference_genome_to_sample,
    add_ska_index,
    add_sourmash_sketch,
    delete_sample_crud,
    get_sample_by_id,
    insert_sample_document,
    pipeline_run_exists_for_sample,
    sample_exists,
)
from bonsai_api.crud.utils import audit_event_context, managed_transaction
from bonsai_api.db import Database
from bonsai_api.exceptions import (
    ConflictError,
    DatabaseOperationError,
    EntryNotFound,
    NotChangedError,
)
from bonsai_api.models.analysis import AnalysisResult, VariantContext
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.genomic_resource import GenomicResourceResponse
from bonsai_api.models.igv import (
    IgvConfig,
    IgvDisplayMode,
    IgvReferenceGenome,
    IgvTrack,
)
from bonsai_api.models.memberships import MembershipEdge
from bonsai_api.models.pipeline import PipelineRun
from bonsai_api.models.reference_genome import ReferenceGenomeResponse
from bonsai_api.models.sample import SampleInfoCreate, SampleRecordDb, SampleRecordOut
from bonsai_api.redis.minhash import (
    schedule_add_genome_signature,
    schedule_add_genome_signature_to_index,
    schedule_remove_genome_signature,
    schedule_remove_genome_signature_from_index,
)
from bonsai_api.services.membership_service import (
    add_memberships,
    get_groups_by_sample_ids,
    remove_memberships,
)
from bonsai_api.services.reference_genomes import get_reference_genome_service
from fastapi import Request
from pydantic import ValidationError
from pymongo.client_session import ClientSession
from pymongo.errors import DuplicateKeyError, PyMongoError

from .analysis_service import get_analysis_service

LOG = logging.getLogger(__name__)


async def create_sample_service(
    db: Database,
    *,
    sample: SampleInfoCreate,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
    session: ClientSession | None = None,
) -> dict[str, Any] | None:
    """Create a new sample document in the database."""
    # verify that groups exists
    if len(sample.groups) > 0 and (
        missing_groups := check_groups_exists(db, group_ids=sample.groups)
    ):
        raise EntryNotFound(
            "One or more groups are not in the database", detail=missing_groups
        )

    # build sample payload
    internal_sample_id = str(uuid.uuid7())
    payload = SampleRecordDb(
        sample_id=internal_sample_id,
        external_sample_id=sample.sample_id,
        sample_name=sample.sample_name,
        lims_id=sample.lims_id,
        groups=sample.groups,
        owners=[ctx.actor.id] or sample.owners,  # default to user that uploaded sample
        owner_organizations=sample.owner_organizations,
        access_groups=sample.access_groups,
        visibility=sample.visibility,
        sequencing=sample.sequencing,
        metadata=sample.metadata,
    )

    event_subject = Subject(id=sample.sample_id, type=SourceType.USR)
    with audit_event_context(audit, "create_sample", ctx, event_subject):
        try:
            # create sample object
            resp = await insert_sample_document(
                db, doc=payload.model_dump(exclude_none=True), session=session
            )
            # create memberships if needed
            if len(sample.groups) > 0:
                edges = [
                    MembershipEdge(sample_id=sample.sample_id, group_id=gr)
                    for gr in sample.groups
                ]
                await add_memberships(db=db, edges=edges, session=session)
        except DuplicateKeyError as dke:
            LOG.error("Duplicate key error while creating group: %s", str(dke))
            raise ConflictError(
                f"Sample with id {sample.sample_id} already exists."
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
        return {
            "inserted_id": str(resp.inserted_id),
            "internal_sample_id": internal_sample_id,
            "external_sample_id": sample.sample_id,
        }


async def delete_sample_service(
    db: Database, *, sample_id: str, session: ClientSession | None = None
) -> dict[str, Any]:
    """Delete a samples from bonsai.

    The delete operation includes removing the sample from groups, and triggering removal of signatures.
    """
    async with managed_transaction(db.client, session) as sess:
        exists = await sample_exists(db, sample_id=sample_id, session=sess)
        if not exists:
            sess.abort_transaction()
            raise EntryNotFound(f"Sample={sample_id} not found!")

        # remove sample from memberships
        memberships = await get_groups_by_sample_ids(
            db, sample_ids=[sample_id], session=sess
        )
        await remove_memberships(memberships, db=db, session=sess)

        status = await delete_sample_crud(db, sample_id=sample_id, session=sess)

        # abort if sample could not be removed
        if not status:
            sess.abort_transaction()
            raise DatabaseOperationError("Something went wrong in the transaction")

        # schedule removal of sourmash data
        rm_job = schedule_remove_genome_signature(sample_id)
        reidx_job = schedule_remove_genome_signature_from_index(
            [sample_id], depends_on=[rm_job.id]
        )

        return {
            "removed_sample": status,
            "remove_sourmash": rm_job.id,
            "remove_sourmash_idx": reidx_job.id,
        }


async def add_pipeline_run_service(
    db: Database,
    *,
    sample_id: str,
    pipeline: PipelineRun,
    session: ClientSession | None = None,
) -> None:
    """Add a pipeline run to an existing sample.

    Raises EntryNotFound if sample missing and ConflictError if a pipeline run already
    exists for the sample.
    """
    if not sample_exists(db, sample_id=sample_id, session=session):
        LOG.error("Sample %s not found when adding pipeline run", sample_id)
        raise EntryNotFound(sample_id)

    if await pipeline_run_exists_for_sample(
        db,
        sample_id=sample_id,
        pipeline_run_id=pipeline.pipeline_run_id,
        session=session,
    ):
        raise ConflictError(
            f"Pipeline run already exists for sample. pipeline_run_id={pipeline.pipeline_run_id}"
        )

    try:
        update_obj = await add_pipeline_run(
            db,
            sample_id=sample_id,
            doc=pipeline.model_dump(exclude_none=True),
            session=session,
        )

        # Ensure update actually modified the document
        if update_obj.modified_count != 1:
            LOG.error(
                "Matched count=%d; Modified count=%d; ",
                update_obj.matched_count,
                update_obj.modified_count,
            )
            raise DatabaseOperationError(f"Failed to add pipeline run for {sample_id}")
    except Exception as exc:  # pragma: no cover - defensive
        LOG.exception("Unexpected error while adding pipeline run: %s", exc)
        raise DatabaseOperationError(str(exc)) from exc


async def get_sample_service(
    db: Database, *, sample_id: str, session: ClientSession | None = None
) -> SampleRecordOut:
    """Retrieve a sample by its sample id."""
    raw_sample = await get_sample_by_id(db, sample_id=sample_id, session=session)

    if raw_sample is None:
        raise EntryNotFound(f"Sample with id '{sample_id}' not found")
    try:
        # get last pipeline run if set
        last_pipeline_run = None
        if (run_id := raw_sample.get("last_pipeline_run_id")) is not None:
            for pr in raw_sample.get("pipeline_runs", []):
                if pr.get("pipeline_run_id") == run_id:
                    last_pipeline_run = pr
                    break

        # merge analysis result and curations into dedicated field for API output
        return SampleRecordOut.model_validate(
            {**raw_sample, "pipeline": last_pipeline_run}
        )
    except ValidationError as ve:
        LOG.error("Validation error when retrieving sample %s: %s", sample_id, str(ve))
        raise DatabaseOperationError(
            f"Data integrity error when retrieving sample {sample_id}: {str(ve)}"
        ) from ve


async def add_ska_index_service(
    db: Database,
    *,
    sample_id: str,
    index_uri: str,
    session: ClientSession | None = None,
    force: bool = False,
):
    """Add a SKA index to a sample."""

    sample = await get_sample_service(db=db, sample_id=sample_id, session=session)

    # check if index has already been added
    if sample.ska_index is not None and not force:
        raise ConflictError(f"Sample {sample_id} is already associated with an index.")

    try:
        update_obj = await add_ska_index(
            db, sample_id=sample_id, index_uri=index_uri, session=session
        )

        # Ensure update actually modified the document
        if update_obj.modified_count != 1:
            raise DatabaseOperationError(f"Failed to add SKA index to {sample_id}")
    except Exception as exc:  # pragma: no cover - defensive
        LOG.exception("Unexpected error while adding SKA index: %s", exc)
        raise DatabaseOperationError(str(exc)) from exc


async def add_sourmash_index_service(
    db: Database, *, sample_id: str, sketch: str, session: ClientSession | None = None
) -> dict[str, str]:
    """Add sourmash index to the database and schedule an addition job."""

    # check that sample exist
    sample = await get_sample_service(db, sample_id=sample_id, session=session)

    if sample.genome_signature is not None:
        raise ConflictError(f"Sample {sample_id} is associated with index")

    # Schedule adding sketch and reindex
    add_sig_job = schedule_add_genome_signature(sample_id, sketch)
    index_job = schedule_add_genome_signature_to_index(
        [sample_id],
        depends_on=[add_sig_job.id],
    )

    # Add job id to sample
    add_idx_job = add_sig_job.id
    resp = await add_sourmash_sketch(
        db, sample_id=sample_id, sketch=add_idx_job, session=session
    )
    if resp.modified_count != 1:
        LOG.error(
            "Matched count=%d; Modified count=%d; ",
            resp.matched_count,
            resp.modified_count,
        )
        raise DatabaseOperationError(f"Failed to add sourmash sketch for {sample_id}")

    return {"add_sketch_job": add_idx_job, "index_job": index_job.id}


async def add_reference_genome_service(
    db: Database,
    *,
    sample_id: str,
    reference_genome_id: str,
    ctx: ApiRequestContext,
    request: Request,
    audit: AuditLogClient | None = None,
    session: ClientSession | None = None,
) -> ReferenceGenomeResponse:
    """Add reference genome to a sample."""
    if not sample_exists(db, sample_id=sample_id, session=session):
        LOG.error("Sample %s not found when adding reference genome", sample_id)
        raise EntryNotFound(sample_id)

    # check that reference genome exist
    ref_genome = await get_reference_genome_service(
        db, resource_id=reference_genome_id, request=request
    )

    event_subject = Subject(id=reference_genome_id, type=SourceType.USR)
    with audit_event_context(audit, "add_reference_genome", ctx, event_subject):
        try:
            update_obj = await add_reference_genome_to_sample(
                db,
                sample_id=sample_id,
                reference_genome_id=reference_genome_id,
                session=session,
            )
        except PyMongoError as pme:
            LOG.error(
                "MongoDB error while adding reference genome to sample: %s", str(pme)
            )
            raise DatabaseOperationError(
                f"Database error occurred adding reference genome to sample: {str(pme)}"
            ) from pme
        except Exception as exc:  # pragma: no cover - defensive
            LOG.exception("Unexpected error while adding a reference genome: %s", exc)
            raise DatabaseOperationError(str(exc)) from exc

        # Ensure update actually modified the document
        if update_obj.modified_count != 1:
            raise NotChangedError("Reference genome was not changed.")
    return ref_genome


def _to_igv_track(resouce: GenomicResourceResponse) -> IgvTrack:
    """Convert GenomicResoucre to IGV track"""
    opts = {}
    if resouce.type == "alignment":
        opts = {
            "display_mode": IgvDisplayMode.SQUISHED,
            "auto_height": True,
            "max_height": 450,
            "show_soft_clips": True,
        }
    if resouce.type == "annotation" and resouce.type == "gff":
        opts = {
            "display_mode": IgvDisplayMode.EXPANDED,
            "height": 120,
            "name_field": "gene",
            "filter_types": ["chromosome", "region", "gene", "exon"],
        }

    return IgvTrack(
        name=resouce.name,
        type=resouce.type,
        format=resouce.format,
        url=resouce.url,
        index_url=resouce.index_url,
        source_type="file",
        **opts,
    )


def _get_variant_positions(
    variant_id: str, *, analysis_obj: AnalysisResult
) -> tuple[int, int] | None:
    """Get variant with ID from sample object."""
    amr_pred = analysis_obj.envelopes.get("amr")
    if not amr_pred:
        return None

    variants = amr_pred.value.get("variants", [])
    for var in variants:
        if not var.get("id") == variant_id:
            continue

        start = var["start"]
        stop = var.get("end") or var["start"]

        if var["variant_type"] == "SV":
            var_length = (stop - start) + 1
            start = round(start - (var_length * 0.1), 0)
            stop = round(stop + (var_length * 0.1), 0)

        return start, stop


async def _build_locus(
    db: Database,
    *,
    variant_ctx: VariantContext,
    reference_name: str,
) -> str:
    """
    Build IGV locus string (e.g. chr1:100-200) from a variant context.

    Returns empty string if variant or positions cannot be found.
    """

    # Fetch analysis
    analysis = await get_analysis_service(
        db, analysis_id=variant_ctx.analysis_id
    )

    if not analysis:
        return ""

    # Extract variant positions
    positions = _get_variant_positions(
        variant_ctx.variant_id,
        analysis_obj=analysis,
    )

    if not positions:
        return ""

    start, stop = positions

    return f"{reference_name}:{start}-{stop}"


async def get_igv_config(
    db: Database,
    *,
    sample_id: str,
    variant_ctx: VariantContext | None,
    request: Request,
) -> IgvConfig:
    """Build a IGV configuration for a sample."""

    # fetch needed resources
    sample_info = await get_sample_service(db, sample_id=sample_id)
    if sample_info.reference_genome_id is None:
        raise EntryNotFound(f"No reference genome associated with sample: {sample_id}")

    ref_genome = await get_reference_genome_service(
        db, resource_id=sample_info.reference_genome_id, request=request
    )

    genomec_resouces = await list_genomic_resources_for_sample_service(db, sample_id=sample_id, request=request)

    # get locus for a variant if variant id was provided
    locus = ""
    if variant_ctx:
        locus = await _build_locus(db, variant_ctx=variant_ctx, reference_name=ref_genome.accession)

    # Build tracks
    tracks = [
        _to_igv_track(tr)
        for tr in itertools.chain(
            ref_genome.reference_tracks, genomec_resouces
        )
    ]

    return IgvConfig(
        locus=locus,
        reference=IgvReferenceGenome(
            name=ref_genome.name,
            fasta_url=ref_genome.fasta_url,
            index_url=ref_genome.fasta_index_url,
        ),
        tracks=tracks,
    )
