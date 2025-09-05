"""Routers for reading or manipulating sample information."""

import logging
import pathlib
from typing import Annotated, Any, Union

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
from fastapi.responses import FileResponse
from prp.models import PipelineResult
from prp.models.phenotype import (
    AMRMethodIndex,
    StressMethodIndex,
    VariantType,
    VirulenceMethodIndex,
)
from prp.models.sample import MethodIndex, ShigaTypingMethodIndex
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from bonsai_api.crud.metadata import add_metadata_to_sample
from bonsai_api.crud.sample import EntryNotFound, add_comment, add_location
from bonsai_api.crud.sample import create_sample as create_sample_record
from bonsai_api.crud.sample import delete_samples as delete_samples_from_db
from bonsai_api.crud.sample import get_sample, get_samples_summary
from bonsai_api.crud.sample import hide_comment as hide_comment_for_sample
from bonsai_api.crud.sample import update_sample as crud_update_sample
from bonsai_api.crud.sample import (
    update_sample_qc_classification,
    update_variant_annotation_for_sample,
)
from bonsai_api.crud.user import get_current_active_user
from bonsai_api.db import Database, get_db
from bonsai_api.io import (
    InvalidRangeError,
    RangeOutOfBoundsError,
    is_file_readable,
    send_partial_file,
)
from bonsai_api.models.base import MultipleRecordsResponseModel
from bonsai_api.models.cluster import TypingMethod
from bonsai_api.models.location import LocationOutputDatabase
from bonsai_api.models.qc import QcClassification, VariantAnnotation
from bonsai_api.models.sample import Comment, CommentInDatabase, SampleInCreate, SampleInDatabase
from bonsai_api.models.metadata import InputMetaEntry
from bonsai_api.models.user import UserOutputDatabase
from bonsai_api.redis import ClusterMethod, ConnectionError
from bonsai_api.redis.minhash import (
    SubmittedJob,
    schedule_add_genome_signature,
    schedule_add_genome_signature_to_index,
    include_in_analysis,
    exclude_from_analysis,
    schedule_find_similar_and_cluster,
    schedule_find_similar_samples,
)
from bonsai_api.utils import format_error_message
from .shared import SAMPLE_ID_PATH, RouterTags, action_from_qc_classification, parse_signature_json

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


class ApiGetSamplesDetailsInput(BaseModel):
    """Input parameters for getting sample details."""

    limit: int | None = Field(default=None, gt=-1, title="Limit the output to x samples")
    skip: int | None = Field(default=None, gt=-1, title="Skip x samples")
    prediction_result: bool = Field(
        default=True, title="Include prediction results"
    )
    qc_metrics: bool = Field(default=False, title="Include QC metrics")
    sid: list[str] | None = Field(
        None, description="Optional limit query to samples ids"
    )


@router.post(
    "/samples/summary",
    response_model_by_alias=False,
    response_model=MultipleRecordsResponseModel,
    tags=[RouterTags.SAMPLE],
)
async def samples_summary(
    query: ApiGetSamplesDetailsInput,
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Entrypoint for getting a summary for multiple samples."""
    db_obj: MultipleRecordsResponseModel = await get_samples_summary(
        db,
        limit=query.limit,
        skip=query.skip,
        prediction_result=query.prediction_result,
        include_samples=query.sid,
        qc_metrics=query.qc_metrics,
    )
    return db_obj


@router.post("/samples/", status_code=status.HTTP_201_CREATED, tags=[RouterTags.SAMPLE])
async def create_sample(
    sample: PipelineResult,
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
) -> dict[str, str]:
    """Entrypoint for creating a new sample."""
    try:
        db_obj = await create_sample_record(db, sample)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.details["errmsg"],
        ) from error
    return {"type": "success", "sample_id": db_obj.sample_id}


@router.delete("/samples/", status_code=status.HTTP_200_OK, tags=[RouterTags.SAMPLE])
async def delete_many_samples(
    sample_ids: list[str],
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
):
    """Delete multiple samples from the database."""
    try:
        result = await delete_samples_from_db(db, sample_ids)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return result


@router.get("/samples/{sample_id}", response_model_by_alias=False, tags=[RouterTags.SAMPLE])
async def read_sample(
    sample_id: str = SAMPLE_ID_PATH,
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
) -> SampleInDatabase:
    """Read sample with sample id from database."""
    try:
        sample_obj = await get_sample(db, sample_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return sample_obj


class UpdateSampleInputModel(BaseModel):
    """Input data when updating sample information."""

    typing: list[Union[MethodIndex, ShigaTypingMethodIndex]]
    phenotype: list[
        Union[VirulenceMethodIndex, AMRMethodIndex, StressMethodIndex, MethodIndex]
    ]


@router.put("/samples/{sample_id}", tags=[RouterTags.SAMPLE], response_model=SampleInDatabase)
async def update_sample(
    update_data: UpdateSampleInputModel,
    sample_id: str = SAMPLE_ID_PATH,
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
):
    """Update sample with sample id from database.

    Take either a partial or full result as input.
    """
    return sample


@router.delete(
    "/samples/{sample_id}", status_code=status.HTTP_200_OK, tags=[RouterTags.SAMPLE]
)
async def delete_sample(
    sample_id: str = SAMPLE_ID_PATH,
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
):
    """Delete the specific sample."""
    try:
        result = await delete_samples_from_db(db, sample_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return result


@router.post("/samples/{sample_id}/metadata", tags=[RouterTags.SAMPLE, RouterTags.META])
async def add_sample_metadata(
    sample_id: str, metadata: list[InputMetaEntry], db: Database = Depends(get_db)) -> bool:
    """Add metadata to an existing sample."""
    try:
        resp = await add_metadata_to_sample(sample_id=sample_id, metadata=metadata, db=db)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))
    except FileExistsError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err))
    return resp


@router.post("/samples/{sample_id}/signature", tags=[RouterTags.SAMPLE])
async def create_genome_signatures_sample(
    sample_id: str,
    signature: str = Depends(parse_signature_json),
    db: Database = Depends(get_db),
) -> dict[str, str]:
    """Entrypoint for uploading a genome signature to the database."""
    # verify that sample are in database
    try:
        sample = await get_sample(db, sample_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=404, detail=format_error_message(error)
        ) from error
    
    # abort if signature has already been added
    sig_exist_err = HTTPException(
        status_code=409, detail="Signature is already added to sample"
    )
    if sample.genome_signature is not None:
        raise sig_exist_err

    add_sig_job = schedule_add_genome_signature(sample_id, signature)
    index_job = schedule_add_genome_signature_to_index(
        [sample_id],
        depends_on=[add_sig_job.id],
    )

    # updated sample in database with signature object jobid
    # recast the data to proper object
    sample_obj: dict[str, Any] = {**sample.model_dump(), **{"genome_signature": add_sig_job.id}}
    upd_sample_data = SampleInCreate.model_validate(sample_obj)
    await crud_update_sample(db, upd_sample_data)

    return {
        "id": sample_id,
        "add_signature_job": add_sig_job.id,
        "index_job": index_job.id,
    }


@router.post("/samples/{sample_id}/ska_index", tags=[RouterTags.SAMPLE])
async def add_ska_index_to_sample(
    sample_id: str,
    index: str,
    db: Database = Depends(get_db),
) -> dict[str, str]:
    """Entrypoint for associating a SKA index with the sample."""
    # verify that sample are in database
    try:
        sample = await get_sample(db, sample_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=404, detail=format_error_message(error)
        ) from error

    # abort if signature has already been added
    idx_exist_err = HTTPException(
        status_code=409, detail="Sample is already associated with an SKA index."
    )
    if sample.ska_index is not None:
        raise idx_exist_err

    # updated sample in database with signature object jobid
    # recast the data to proper object
    sample_obj = {**sample.model_dump(), **{"ska_index": index}}
    upd_sample_data = SampleInCreate(**sample_obj)
    await crud_update_sample(db, upd_sample_data)

    return {"sample_id": sample_id, "index_file": index}


@router.get("/samples/{sample_id}/alignment", tags=[RouterTags.SAMPLE])
async def get_sample_read_mapping(
    sample_id: str,
    index: bool = Query(False),
    range: Annotated[str | None, Header()] = None,
    db: Database = Depends(get_db),
) -> str:
    """Get read mapping results for a sample."""
    try:
        sample = await get_sample(db, sample_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=format_error_message(error)
        ) from error

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
    db: Database = Depends(get_db),
) -> str:
    """Get vcfs associated with the sample."""
    # verify that sample are in database
    try:
        sample = await get_sample(db, sample_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=404, detail=format_error_message(error)
        ) from error

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
    db: Database = Depends(get_db),
) -> dict[str, str]:
    """Entrypoint for uploading varants in vcf format to the sample."""
    # verify that sample are in database
    try:
        sample = await get_sample(db, sample_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=404, detail=format_error_message(error)
        ) from error

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
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> bool:
    """Update sample QC status."""
    try:
        # dont update if the status dont change
        sample = await get_sample(db, sample_id)
        if sample.qc_status == QcClassification:
            return True
        
        # update
        status_obj: bool = await update_sample_qc_classification(
            db, sample_id, classification
        )

        # update if status should be excluded from indexing
        action = action_from_qc_classification(classification)
        if action == "include":
            include_in_analysis(sample_id)
        else:
            exclude_from_analysis(sample_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return status_obj


@router.put(
    "/samples/{sample_id}/resistance/variants",
    response_model_by_alias=False,
    tags=[RouterTags.SAMPLE],
)
async def update_variant_annotation(
    classification: VariantAnnotation,
    sample_id: str = SAMPLE_ID_PATH,
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> SampleInDatabase:
    """Update manual annotation of one or more variants."""
    try:
        sample_info: SampleInDatabase = await update_variant_annotation_for_sample(
            db, sample_id, classification, username=current_user.username
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return sample_info


@router.post(
    "/samples/{sample_id}/comment",
    response_model=CommentsObj,
    tags=[RouterTags.SAMPLE],
)
async def post_comment(
    comment: Comment,
    sample_id: str = SAMPLE_ID_PATH,
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> CommentsObj:
    """Add a commet to a sample."""
    try:
        comment_obj: CommentsObj = await add_comment(db, sample_id, comment)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error,
        ) from error
    return comment_obj


@router.delete(
    "/samples/{sample_id}/comment/{comment_id}",
    tags=[RouterTags.SAMPLE],
)
async def hide_comment(
    sample_id: str = SAMPLE_ID_PATH,
    comment_id: int = Path(..., title="ID of the comment to delete"),
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
) -> bool:
    """Hide a comment in a sample from users."""
    try:
        resp: bool = await hide_comment_for_sample(db, sample_id, comment_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error,
        ) from error
    return resp


@router.put(
    "/samples/{sample_id}/location",
    response_model=LocationOutputDatabase,
    tags=[RouterTags.SAMPLE, "locations"],
)
async def update_location(
    location_id: str = Body(...),
    sample_id: str = SAMPLE_ID_PATH,
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> LocationOutputDatabase:
    """Update the location of a sample."""
    try:
        location_obj: LocationOutputDatabase = await add_location(
            db, sample_id, location_id
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error,
        ) from error
    return location_obj


class SimilarSamplesInput(BaseModel):  # pylint: disable=too-few-public-methods
    """Input parameters for finding similar samples."""

    limit: int | None = Field(default=10, gt=-1, title="Limit the output to x samples")
    similarity: float = Field(default=0.5, gt=0, title="Similarity threshold")
    cluster: bool = Field(default=False, title="Cluster the similar")
    typing_method: TypingMethod | None = Field(
        None, title="Cluster using a specific typing method"
    )
    cluster_method: ClusterMethod | None = Field(None, title="Cluster the similar")


@router.post(
    "/samples/{sample_id}/similar",
    response_model=SubmittedJob,
    tags=["minhash", RouterTags.SAMPLE],
)
async def find_similar_samples(
    body: SimilarSamplesInput,
    sample_id: str = SAMPLE_ID_PATH,
    db: Database = Depends(get_db),
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
            submission_info: SubmittedJob = schedule_find_similar_and_cluster(
                sample_id,
                min_similarity=body.similarity,
                limit=body.limit,
                typing_method=body.typing_method,
                cluster_method=body.cluster_method,
            )
        else:
            submission_info: SubmittedJob = schedule_find_similar_samples(
                sample_id,
                min_similarity=body.similarity,
                limit=body.limit,
            )
    except ConnectionError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error))
    except NotImplementedError as error:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(error))
    return submission_info
