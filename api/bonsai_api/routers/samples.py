"""Routers for reading or manipulating sample information."""

import logging
import pathlib
from typing import Annotated, Any, cast

from bonsai_api.exceptions import DatabaseOperationError
from bonsai_api.models.pipeline import PipelineRun
from api_client.audit_log.client import AuditLogClient
from bonsai_api.crud.builder.summary_manifest import MANIFEST
from bonsai_api.crud.builder.types import ManifestOutput
from bonsai_api.crud.metadata import add_metadata_to_sample
from bonsai_api.crud.sample import (
    EntryNotFound,
    add_comment,
    add_location,
)
from bonsai_api.services.sample_service import add_pipeline_run_service, create_sample_service, get_sample_service, add_ska_index_service, add_sourmash_index_service
from bonsai_api.crud.sample import delete_samples as delete_samples_from_db
from bonsai_api.crud.sample import (
    get_samples_full,
)
from bonsai_api.crud.sample import hide_comment as hide_comment_for_sample
from bonsai_api.crud.sample import update_sample as crud_update_sample
from bonsai_api.crud.sample import (
    update_sample_qc_classification,
    update_variant_annotation_for_sample,
)
from bonsai_api.crud.summary import get_samples_summary
from bonsai_api.db import Database
from bonsai_api.dependencies import (
    get_audit_log,
    get_current_active_user,
    get_database,
    get_request_context,
)
from bonsai_api.io import (
    InvalidRangeError,
    RangeOutOfBoundsError,
    is_file_readable,
    send_partial_file,
)
from bonsai_api.models.base import MultipleRecordsResponseModel
from bonsai_api.models.cluster import TypingMethod
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.location import LocationOutputDatabase
from bonsai_api.models.metadata import InputMetaEntry
from bonsai_api.models.qc import QcClassification, VariantAnnotation
from bonsai_api.models.sample import (
    Comment,
    CommentInDatabase,
    SampleInCreate,
    SampleRecordDb,
    SampleInfoCreate,
    SampleRecordOut,
)
from bonsai_api.models.user import UserOutputDatabase
from bonsai_api.redis import ClusterMethod, ConnectionError
from bonsai_api.redis.minhash import (
    SubmittedJob,
    exclude_from_analysis,
    include_in_analysis,
    schedule_add_genome_signature_to_index,
    schedule_find_similar_and_cluster,
    schedule_find_similar_samples,
    schedule_remove_genome_signature_from_index,
)
from bonsai_api.utils import format_error_message
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Header,
    HTTPException,
    Path,
    Query,
    Security,
    status,
)
from fastapi.responses import FileResponse, JSONResponse
from prp.parse.models.enums import VariantType
from pydantic import BaseModel, Field, ValidationError, model_validator

from .shared import (
    SAMPLE_ID_PATH,
    RouterTags,
    action_from_qc_classification,
    parse_signature_json,
)
from bonsai_api.models.sample import MethodIndex

CommentsObj = list[CommentInDatabase]
LOG = logging.getLogger(__name__)
router = APIRouter()


class SearchParams(BaseModel):  # pylint: disable=too-few-public-methods
    """Parameters for searching for samples."""

    sample_id: str | list[str]


class SearchBody(BaseModel):  # pylint: disable=too-few-public-methods
    """Parameters for searching for samples."""

    params: SearchParams
    order: str = "1"
    limit: int | None = None
    skip: int = 0


READ_PERMISSION = "samples:read"
WRITE_PERMISSION = "samples:write"
UPDATE_PERMISSION = "samples:update"


class SamplesSummaryBody(BaseModel):
    """Input parameters for getting sample details."""

    group_id: str | None = None
    sid: list[str] | None = Field(
        None, description="Optional limit query to samples ids"
    )
    fields: list[str] | None = None
    sort: str = "-created_at"
    limit: int | None = Field(default=None, title="Limit the output to x samples")
    offset: int = Field(0, ge=0)


@router.post("/samples/summary")
async def query_samples(
    body: SamplesSummaryBody,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Get samples."""
    match = {}
    if body.group_id:
        match["groups"] = body.group_id
    if body.sid:
        match["sample_id"] = {"$in": body.sid}

    try:
        return await get_samples_summary(
            db,
            MANIFEST,
            match=match,
            fields=body.fields,
            sort=body.sort,
            limit=body.limit,
            offset=body.offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


@router.get("/samples/summary/manifest")
async def get_summary_manifest():
    """Get valid fields for the sample summary."""
    public = ManifestOutput.from_internals(MANIFEST)
    resp = JSONResponse(content=public.model_dump(exclude_none=True))
    resp.headers["ETag"] = public.etag
    return resp


@router.get(
    "/samples", tags=[RouterTags.SAMPLE], response_model=MultipleRecordsResponseModel
)
async def list_samples(
    group_id: str | None = Query(None, description="Filter group by ID"),
    sid: list[str] | None = Query(
        None, description="Fileter by sample ids (Use POST for large sets)"
    ),
    fields: list[str] | None = Query(None, description="Fields to include in response"),
    sort: str = Query("-created_at"),
    limit: int = Query(50, ge=0),
    offset: int = Query(0, ge=0),
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Get samples from the database. It can return either the full or summarized sample information."""
    try:
        match = {}
        if group_id:
            match["groups"] = group_id
        if sid:
            match["sample_id"] = {"$in": sid}

        return await get_samples_full(
            db=db, match=match, fields=fields, sort=sort, limit=limit, offset=offset
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


@router.post("/samples/", status_code=status.HTTP_201_CREATED, tags=[RouterTags.SAMPLE])
async def create_sample(
    sample: SampleInfoCreate,
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
) -> dict[str, str]:
    """Entrypoint for creating a new sample."""
    resp = await create_sample_service(db, sample=sample, ctx=req_ctx, audit=audit_log)
    return {"type": "success", **resp}


@router.delete("/samples/", status_code=status.HTTP_200_OK, tags=[RouterTags.SAMPLE])
async def delete_many_samples(
    sample_ids: list[str],
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
):
    """Delete multiple samples from the database."""
    return await delete_samples_from_db(
        db, sample_ids, ctx=req_ctx, audit=audit_log
    )


@router.get(
    "/samples/{sample_id}", response_model_by_alias=False, tags=[RouterTags.SAMPLE]
)
async def read_sample(
    sample_id: str = SAMPLE_ID_PATH,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
) -> SampleRecordOut:
    """Read sample with sample id from database."""
    return await get_sample_service(db, sample_id=sample_id)


class UpdateSampleInputModel(BaseModel):
    """Input data when updating sample information."""

    typing: list[MethodIndex]
    phenotype: list[MethodIndex]


@router.put(
    "/samples/{sample_id}", tags=[RouterTags.SAMPLE], response_model=SampleRecordDb
)
async def update_sample(
    update_data: UpdateSampleInputModel,
    sample_id: str = SAMPLE_ID_PATH,
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
):
    """Update sample with sample id from database.

    Take either a partial or full result as input.
    """
    return sample_id


@router.delete(
    "/samples/{sample_id}", status_code=status.HTTP_200_OK, tags=[RouterTags.SAMPLE]
)
async def delete_sample(
    sample_id: str = SAMPLE_ID_PATH,
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
):
    """Delete the specific sample."""
    return await delete_samples_from_db(db, [sample_id], req_ctx, audit_log)


@router.post("/samples/{sample_id}/metadata", tags=[RouterTags.SAMPLE, RouterTags.META])
async def add_sample_metadata(
    sample_id: str, metadata: list[InputMetaEntry], db: Database = Depends(get_database)
) -> bool:
    """Add metadata to an existing sample."""
    try:
        resp = await add_metadata_to_sample(
            sample_id=sample_id, metadata=metadata, db=db
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)
        )
    except FileExistsError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err))
    return resp


@router.post("/samples/{sample_id}/pipeline-runs", tags=[RouterTags.SAMPLE, RouterTags.PIPELINE_RUNS])
async def add_pipeline_run(
    sample_id: str,
    body: PipelineRun,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Add a pipeline analysis run to a existing sample."""
    try:
        return await add_pipeline_run_service(db, sample_id=sample_id, pipeline=body)
    except DatabaseOperationError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/samples/{sample_id}/signature", tags=[RouterTags.SAMPLE])
async def create_genome_signatures_sample(
    sample_id: str,
    signature: str = Depends(parse_signature_json),
    db: Database = Depends(get_database),
) -> dict[str, str]:
    """Entrypoint for uploading a genome signature to the database."""

    job_ids = await add_sourmash_index_service(db, sample_id=sample_id, sketch=signature)
    return {
        "id": sample_id,
        "add_signature_job": job_ids["add_sketch_job"],
        "index_job": job_ids["index_job"],
    }


@router.post("/samples/{sample_id}/ska_index", tags=[RouterTags.SAMPLE])
async def add_ska_index_to_sample(
    sample_id: str,
    index: str = Body(...),
    db: Database = Depends(get_database),
) -> dict[str, str]:
    """Entrypoint for associating a SKA index with the sample."""

    await add_ska_index_service(db, sample_id=sample_id, index_uri=index)

    return {"sample_id": sample_id, "index_file": index}


@router.get("/samples/{sample_id}/alignment", tags=[RouterTags.SAMPLE])
async def get_sample_read_mapping(
    sample_id: str,
    index: bool = Query(False),
    range: Annotated[str | None, Header()] = None,
    db: Database = Depends(get_database),
) -> str:
    """Get read mapping results for a sample."""
    sample = await get_sample_service(db, sample_id=sample_id)

    if sample.read_mapping is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No read mapping results associated with sample",
        )

    # build path to either bam or the index
    if index:
        file_path = pathlib.Path(f"{sample.read_mapping}.bai")
    else:
        file_path = pathlib.Path(sample.read_mapping)
    # test if file is readable
    if not is_file_readable(str(file_path)):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Alignment file could not be processed",
        )

    # send file if byte range is not set
    if range is None:
        response = FileResponse(file_path)
    else:
        try:
            response = send_partial_file(file_path, range)
        except InvalidRangeError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error
        except RangeOutOfBoundsError as error:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail=str(error),
            ) from error
    return response


@router.get("/samples/{sample_id}/vcf", tags=[RouterTags.SAMPLE])
async def get_vcf_files_for_sample(
    sample_id: str = Path(...),
    variant_type: VariantType = Query(...),
    range: Annotated[str | None, Header()] = None,
    db: Database = Depends(get_database),
) -> str:
    """Get vcfs associated with the sample."""
    # verify that sample are in database
    sample = await get_sample_service(db, sample_id=sample_id)

    # build path to the VCF
    file_path = None
    for annot in sample.genome_annotation:
        path = pathlib.Path(annot.file)
        # if file exist
        if variant_type.value == annot.name:
            file_path = path
            break

    if file_path is None:
        LOG.error("HTTP 404: %s - %s", sample_id, variant_type)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No read mapping results associated with sample",
        )
    # test if file is readable
    if not is_file_readable(str(file_path)):
        LOG.error("HTTP 500: %s - %s", sample_id, variant_type)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Alignment file could not be processed",
        )

    # send file if byte range is not set
    if range is None:
        response = FileResponse(file_path)
    else:
        try:
            response = send_partial_file(file_path, range)
        except InvalidRangeError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error
        except RangeOutOfBoundsError as error:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail=str(error),
            ) from error
    return response


@router.post("/samples/{sample_id}/vcf", tags=[RouterTags.SAMPLE])
async def add_vcf_to_sample(
    sample_id: str,
    vcf: Annotated[bytes, File()],
    db: Database = Depends(get_database),
) -> dict[str, str]:
    """Entrypoint for uploading varants in vcf format to the sample."""
    # verify that sample are in database
    sample = await get_sample_service(db, sample_id=sample_id)

    # updated sample in database with signature object jobid
    # recast the data to proper object
    sample_obj = {**sample.model_dump(), **{"str_variants": ""}}
    upd_sample_data = SampleInCreate(**sample_obj)
    await crud_update_sample(db, upd_sample_data)

    return {"id": sample_id, "n_variants": 0}


@router.put(
    "/samples/{sample_id}/qc_status",
    response_model=QcClassification,
    tags=[RouterTags.SAMPLE],
)
async def update_qc_status(
    classification: QcClassification,
    sample_id: str = SAMPLE_ID_PATH,
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> bool:
    """Update sample QC status."""

    # dont update if the status dont change
    sample = await get_sample_service(db, sample_id=sample_id)
    if sample.qc_status == classification:
        return True

    # update
    status_obj: bool = await update_sample_qc_classification(
        db, sample_id, classification, ctx=req_ctx, audit=audit_log
    )

    # update if status should be excluded from indexing
    action = action_from_qc_classification(classification)
    if action == "include":
        include_job = include_in_analysis(sample_id)
        schedule_add_genome_signature_to_index(
            [sample_id],
            depends_on=[include_job.id],
        )
    else:
        # run exclude job and then remove signature from index
        exclude_job = exclude_from_analysis(sample_id)
        schedule_remove_genome_signature_from_index(
            [sample_id],
            depends_on=[exclude_job.id],
        )
    return status_obj


@router.put(
    "/samples/{sample_id}/resistance/variants",
    response_model_by_alias=False,
    tags=[RouterTags.SAMPLE],
)
async def update_variant_annotation(
    classification: VariantAnnotation,
    sample_id: str = SAMPLE_ID_PATH,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> SampleRecordDb:
    """Update manual annotation of one or more variants."""
    return await update_variant_annotation_for_sample(
        db, sample_id, classification, username=current_user.username
    )


@router.post(
    "/samples/{sample_id}/comment",
    response_model=CommentsObj,
    tags=[RouterTags.SAMPLE],
)
async def post_comment(
    comment: Comment,
    sample_id: str = SAMPLE_ID_PATH,
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> CommentsObj:
    """Add a commet to a sample."""
    return await add_comment(
        db, sample_id, comment, req_ctx, audit_log
    )


@router.delete(
    "/samples/{sample_id}/comment/{comment_id}",
    tags=[RouterTags.SAMPLE],
)
async def hide_comment(
    sample_id: str = SAMPLE_ID_PATH,
    comment_id: int = Path(..., title="ID of the comment to delete"),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
) -> bool:
    """Hide a comment in a sample from users."""
    return await hide_comment_for_sample(
        db, sample_id, comment_id, req_ctx, audit_log
    )


@router.put(
    "/samples/{sample_id}/location",
    response_model=LocationOutputDatabase,
    tags=[RouterTags.SAMPLE, "locations"],
)
async def update_location(
    location_id: str = Body(...),
    sample_id: str = SAMPLE_ID_PATH,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> LocationOutputDatabase:
    """Update the location of a sample."""
    return await add_location(
        db, sample_id, location_id
    )


class SearchSimilarInput(BaseModel):  # pylint: disable=too-few-public-methods
    """Input parameters for finding similar samples."""

    limit: int | None = Field(default=10, ge=1, title="Limit the output to x samples")
    similarity: float = Field(default=0.5, gt=0, le=1, title="Similarity threshold")
    cluster: bool = Field(
        default=False,
        title="Cluster the similar",
        description="If the samples found with similar search should be clustered.",
    )
    narrow_to_sample_ids: list[str] | None = Field(
        default=None,
        description="Restrict the similarity search to these sample IDs. If None, search across all samples.",
        examples=[["sample_id"]],
    )
    typing_method: TypingMethod | None = Field(
        default=None, title="Cluster using a specific typing method"
    )
    cluster_method: ClusterMethod | None = Field(
        default=None, title="Cluster the similar"
    )

    @model_validator(mode="after")
    def validate_cluster_settings(self):
        """Validate that cluster settings are defined if cluster=True."""
        if self.cluster and (self.cluster_method is None or self.typing_method is None):
            raise ValidationError(
                "'cluster_method' and 'typing_method' must be set if 'cluster' is True."
            )
        return self


@router.post(
    "/samples/{sample_id}/similar",
    response_model=SubmittedJob,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["minhash", RouterTags.SAMPLE],
)
async def find_similar_samples(
    body: SearchSimilarInput,
    sample_id: str = SAMPLE_ID_PATH,
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
) -> SubmittedJob:
    """Find similar samples using minhash distance.

    The entrypoint adds a similarity search job to the redis
    queue.
    """
    LOG.info("ref: %s, body: %s, cluster: %s", sample_id, body, body.cluster)
    try:
        if body.cluster:
            typing_method = cast(TypingMethod, body.typing_method)
            cluster_method = cast(ClusterMethod, body.cluster_method)
            submission_info: SubmittedJob = schedule_find_similar_and_cluster(
                sample_id,
                min_similarity=body.similarity,
                limit=body.limit,
                narrow_to_sample_ids=body.narrow_to_sample_ids,
                typing_method=typing_method,
                cluster_method=cluster_method,
            )
        else:
            submission_info: SubmittedJob = schedule_find_similar_samples(
                sample_id,
                min_similarity=body.similarity,
                limit=body.limit,
                narrow_to_sample_ids=body.narrow_to_sample_ids,
            )
    except ConnectionError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
        ) from error
    return submission_info
