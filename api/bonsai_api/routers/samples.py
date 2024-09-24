"""Routers for reading or manipulating sample information."""

import logging
import pathlib
from typing import Annotated, Any, Dict, List

from fastapi import (
    APIRouter,
    Body,
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
from prp.models.phenotype import VariantType
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from ..crud.sample import EntryNotFound, add_comment, add_location
from ..crud.sample import create_sample as create_sample_record
from ..crud.sample import delete_samples as delete_samples_from_db
from ..crud.sample import get_sample, get_samples_summary
from ..crud.sample import hide_comment as hide_comment_for_sample
from ..crud.sample import update_sample as crud_update_sample
from ..crud.sample import (
    update_sample_qc_classification,
    update_variant_annotation_for_sample,
)
from ..crud.user import get_current_active_user
from ..db import db
from ..io import (
    InvalidRangeError,
    RangeOutOfBoundsError,
    is_file_readable,
    send_partial_file,
)
from ..models.location import LocationOutputDatabase
from ..models.qc import QcClassification, VariantAnnotation
from ..models.sample import (
    SAMPLE_ID_PATTERN,
    Comment,
    CommentInDatabase,
    SampleInCreate,
    SampleInDatabase,
)
from ..models.user import UserOutputDatabase
from ..models.base import MultipleRecordsResponseModel
from ..redis import ClusterMethod, TypingMethod
from ..redis.minhash import (
    SubmittedJob,
    schedule_add_genome_signature,
    schedule_add_genome_signature_to_index,
    schedule_find_similar_and_cluster,
    schedule_find_similar_samples,
)
from ..utils import format_error_message

CommentsObj = List[CommentInDatabase]
LOG = logging.getLogger(__name__)
router = APIRouter()


class SearchParams(BaseModel):  # pylint: disable=too-few-public-methods
    """Parameters for searching for samples."""

    sample_id: str | List[str]


class SearchBody(BaseModel):  # pylint: disable=too-few-public-methods
    """Parameters for searching for samples."""

    params: SearchParams
    order: str = 1
    limit: int | None = None
    skip: int = 0


DEFAULT_TAGS = [
    "samples",
]
READ_PERMISSION = "samples:read"
WRITE_PERMISSION = "samples:write"
UPDATE_PERMISSION = "samples:update"


@router.get(
    "/samples/",
    response_model_by_alias=False,
    response_model=MultipleRecordsResponseModel,
    tags=DEFAULT_TAGS,
)
async def samples_summary(
    limit: int = Query(10, gt=-1),
    skip: int = Query(0, gt=-1),
    prediction_result: bool = Query(True, description="Include prediction results"),
    qc_metrics: bool = Query(False, description="Include QC metrics"),
    sid: list[str] = Query([], description="Optional limit query to samples ids"),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Entrypoint for getting a summary for multiple samples."""
    # query samples
    db_obj: MultipleRecordsResponseModel = await get_samples_summary(
        db,
        limit=limit,
        skip=skip,
        prediction_result=prediction_result,
        include_samples=sid,
        qc_metrics=qc_metrics,
    )
    return db_obj


@router.post("/samples/", status_code=status.HTTP_201_CREATED, tags=DEFAULT_TAGS)
async def create_sample(
    sample: PipelineResult,
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
) -> Dict[str, str]:
    """Entrypoint for creating a new sample.

    :param sample: JASEN prediction result
    :type sample: PipelineResult
    :param current_user: The logged in user, defaults to Security
    :type current_user: UserOutputDatabase, optional
    :raises HTTPException: Return 409 error if sample is already in the database.
    :return: record id in the database
    :rtype: Dict[str, str]
    """
    try:
        db_obj = await create_sample_record(db, sample)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.details["errmsg"],
        ) from error
    return {"type": "success", "sample_id": db_obj.sample_id}


@router.delete("/samples/", status_code=status.HTTP_200_OK, tags=DEFAULT_TAGS)
async def delete_many_samples(
    sample_ids: List[str],
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


@router.get("/samples/{sample_id}", response_model_by_alias=False, tags=DEFAULT_TAGS)
async def read_sample(
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
) -> SampleInDatabase:
    """Read sample with sample id from database.

    :param sample_id: Sample id, defaults to Path
    :type sample_id: str, optional
    :param current_user: for authentication, defaults to Security
    :type current_user: UserOutputDatabase, optional
    :raises HTTPException: Return 404 error if sample is not in the database.
    :return: Sample prediction results.
    :rtype: SampleInDatabase
    """
    try:
        sample_obj = await get_sample(db, sample_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return sample_obj


@router.put("/samples/{sample_id}", tags=DEFAULT_TAGS)
async def update_sample(
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    sample: Dict | PipelineResult = Body({}),
    location: Dict = Body({}, embed=True),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> Dict[str, str | SampleInDatabase]:
    """Update sample with sample id from database.

    :param sample_id: Sample id, defaults to Path
    :type sample_id: str, optional
    :param sample: New sample information, defaults to Body({})
    :type sample: Dict | PipelineResult, optional
    :param location: Location information, defaults to Body({}, embed=True)
    :type location: Dict, optional
    :param current_user: for authentication, defaults to Security
    :type current_user: UserOutputDatabase, optional
    :return: _description_
    :rtype: Dict[str, str | SampleInDatabase]
    """
    return {"sample_id": sample_id, "sample": sample, "location": location}


@router.delete(
    "/samples/{sample_id}", status_code=status.HTTP_200_OK, tags=DEFAULT_TAGS
)
async def delete_sample(
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
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


@router.post("/samples/{sample_id}/signature", tags=DEFAULT_TAGS)
async def create_genome_signatures_sample(
    sample_id: str,
    signature: Annotated[bytes, File()],
) -> Dict[str, str]:
    """Entrypoint for uploading a genome signature to the database.

    :param sample_id: Sample id
    :type sample_id: str
    :param signature: Sourmash genome signature file
    :type signature: Annotated[bytes, File
    :raises HTTPException: Return 404 error if sample has not been uploaded
    :raises sig_exist_err: Return 409 error if signature already has been uploaded
    :return: Ids for upload and indexing job
    :rtype: Dict[str, str]
    """
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
    sample_obj = {**sample.model_dump(), **{"genome_signature": add_sig_job.id}}
    upd_sample_data = SampleInCreate(**sample_obj)
    await crud_update_sample(db, upd_sample_data)

    return {
        "id": sample_id,
        "add_signature_job": add_sig_job.id,
        "index_job": index_job.id,
    }


@router.get("/samples/{sample_id}/alignment", tags=DEFAULT_TAGS)
async def get_sample_read_mapping(
    sample_id: str,
    index: bool = Query(False),
    range: Annotated[str | None, Header()] = None,
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


@router.get("/samples/{sample_id}/vcf", tags=DEFAULT_TAGS)
async def get_vcf_files_for_sample(
    sample_id: str = Path(...),
    variant_type: VariantType = Query(...),
    range: Annotated[str | None, Header()] = None,
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


@router.post("/samples/{sample_id}/vcf", tags=DEFAULT_TAGS)
async def add_vcf_to_sample(
    sample_id: str,
    vcf: Annotated[bytes, File()],
) -> Dict[str, str]:
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
    tags=DEFAULT_TAGS,
)
async def update_qc_status(
    classification: QcClassification,
    sample_id: str = Path(
        ...,
        title="ID of the sample",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> bool:
    """Update sample QC status

    :param classification: QC classification info
    :type classification: QcClassification
    :param sample_id: Sample id, defaults to Path
    :type sample_id: str, optional
    :param current_user: for authentication, defaults to Security
    :type current_user: UserOutputDatabase, optional
    :raises HTTPException: Return 404 error if sample is not in the database
    :return: Sample information in the database.
    :rtype: bool
    """
    try:
        status_obj: bool = await update_sample_qc_classification(
            db, sample_id, classification
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return status_obj


@router.put(
    "/samples/{sample_id}/resistance/variants",
    response_model_by_alias=False,
    tags=DEFAULT_TAGS,
)
async def update_variant_annotation(
    classification: VariantAnnotation,
    sample_id: str = Path(
        ...,
        title="ID of the sample",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
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
    tags=DEFAULT_TAGS,
)
async def post_comment(
    comment: Comment,
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> CommentsObj:
    """Add a commet to a sample.

    :param comment: Comment information
    :type comment: Comment
    :param sample_id: Sample id, defaults to Path
    :type sample_id: str, optional
    :param current_user: for authentication, defaults to Security
    :type current_user: UserOutputDatabase, optional
    :raises HTTPException: Return 404 HTTP error if sample have not been added to the database.
    :return: All comments for sample.
    :rtype: CommentsObj
    """
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
    tags=DEFAULT_TAGS,
)
async def hide_comment(
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    comment_id: int = Path(..., title="ID of the comment to delete"),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
) -> bool:
    """Hide a comment in a sample from users.

    :param sample_id: Sample id, defaults to Path
    :type sample_id: str, optional
    :param comment_id: Comment id, defaults to Path(..., title="ID of the comment to delete")
    :type comment_id: int, optional
    :param current_user: for authentication, defaults to Security
    :type current_user: UserOutputDatabase, optional
    :raises HTTPException: Return 404 error if comment or sample is not in the database.
    :return: operation status.
    :rtype: bool
    """
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
    tags=[*DEFAULT_TAGS, "locations"],
)
async def update_location(
    location_id: str = Body(...),
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> LocationOutputDatabase:
    """Update the location of a sample.

    :param location_id: id of the location, defaults to Body(...)
    :type location_id: str, optional
    :param sample_id: Sample id, defaults to Path
    :type sample_id: str, optional
    :param current_user: for authentication, defaults to Security
    :type current_user: UserOutputDatabase, optional
    :raises HTTPException: Return a 404 error if sample or location is not in the database.
    :return: The associated location.
    :rtype: LocationOutputDatabase
    """
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
    tags=["minhash", *DEFAULT_TAGS],
)
async def find_similar_samples(
    body: SimilarSamplesInput,
    sample_id: str = Path(
        ...,
        title="ID of the refernece sample",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
) -> SubmittedJob:
    """Find similar samples using minhash distance.

    The entrypoint adds a similarity search job to the redis
    queue.

    :param body: Query information
    :type body: SimilarSamplesInput
    :param sample_id: Sample id, defaults to Path
    :type sample_id: str, optional
    :param current_user: for authentication, defaults to Security
    :type current_user: UserOutputDatabase, optional
    :return: The information of the submitted job.
    :rtype: SubmittedJob
    """
    LOG.info("ref: %s, body: %s, cluster: %s", sample_id, body, body.cluster)
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
    return submission_info
