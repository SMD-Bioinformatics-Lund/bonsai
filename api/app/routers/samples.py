import logging
import pathlib
from typing import Annotated, Dict, List

from pymongo.errors import DuplicateKeyError

from pydantic import BaseModel, Field
from fastapi import (APIRouter, Body, File, HTTPException, Path, Query,
                     Security, status)

from ..crud.sample import (EntryNotFound, add_comment, add_location)
from ..crud.sample import create_sample as create_sample_record
from ..crud.sample import get_sample, get_samples_summary
from ..crud.sample import hide_comment as hide_comment_for_sample
from ..crud.sample import update_sample as crud_update_sample
from ..crud.sample import update_sample_qc_classification
from ..crud.minhash import (schedule_add_genome_signature, 
                            schedule_add_genome_signature_to_index,
                            schedule_find_similar_samples,
                            schedule_find_similar_and_cluster,
                            SubmittedJob
                            )
from ..crud.user import get_current_active_user
from ..db import db
from ..models.location import LocationOutputDatabase
from ..models.qc import QcClassification
from ..models.sample import (SAMPLE_ID_PATTERN, Comment, CommentInDatabase,
                             PipelineResult, SampleInCreate)
from ..models.user import UserOutputDatabase
from ..utils import format_error_message
from ..internal.cluster import ClusterMethod, TypingMethod

LOG = logging.getLogger(__name__)
router = APIRouter()

class SearchParams(BaseModel):
    """Parameters for searching for samples."""

    sample_id: str | List[str]


class SearchBody(BaseModel):
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


@router.get("/samples/", tags=DEFAULT_TAGS)
async def read_samples(
    limit: int = Query(10, gt=-1),
    skip: int = Query(0, gt=-1),
    offset: int = Query(0, gt=-1),
    include_qc: bool = Query(True),
    include_mlst: bool = Query(True),
    # include_cgmlst: bool = Query(True),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    # skip and offset function the same
    skip = max([offset, skip])
    db_obj = await get_samples_summary(
        db,
        limit=limit,
        skip=skip,
        include_qc=include_qc,
        include_mlst=include_mlst,
    )
    return {"status": "success", "total": len(db_obj), "records": db_obj}


@router.post("/samples/", status_code=status.HTTP_201_CREATED, tags=DEFAULT_TAGS)
async def create_sample(
    sample: PipelineResult,
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    try:
        db_obj = await create_sample_record(db, sample)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.details["errmsg"],
        )
    return {"type": "success", "id": db_obj.id}


@router.post("/samples/search", tags=DEFAULT_TAGS)
async def search_samples(
    body: SearchBody,
    current_user: UserOutputDatabase = Security(get_current_active_user, scopes=[READ_PERMISSION]),
    ):
    """Search for multiple samples."""
    sample_ids = body.params.sample_id
    # to list if sample ids is a string
    if isinstance(sample_ids, str):
        sample_ids = [sample_ids]
    # query samples
    db_obj = await get_samples_summary(
        db,
        include=sample_ids,
        limit=body.limit,
        skip=body.skip,
    )
    return {"status": "success", "total": len(db_obj), "records": db_obj}


@router.get("/samples/{sample_id}", tags=DEFAULT_TAGS)
async def read_sample(
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    try:
        sample_obj = await get_sample(db, sample_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
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
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    return {"sample_id": sample_id, "sample": sample, "location": location}
    try:
        comment_obj = await add_location(db, sample_id, location_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return comment_obj


@router.post("/samples/{sample_id}/signature", tags=DEFAULT_TAGS)
async def create_genome_signatures_sample(
    sample_id: str,
    signature: Annotated[bytes, File()],
):
    # verify that sample are in database
    try:
        sample = await get_sample(db, sample_id)
    except EntryNotFound as err:
        raise HTTPException(status_code=404, detail=format_error_message(err))

    # abort if signature has already been added
    sig_exist_err = HTTPException(
        status_code=409, detail="Signature is already added to sample"
    )
    if sample.genome_signature is not None:
        raise sig_exist_err

    add_sig_job = schedule_add_genome_signature(sample_id, signature)
    index_job = schedule_add_genome_signature_to_index([sample_id], depends_on=[add_sig_job.id])

    # updated sample in database with signature object jobid
    # recast the data to proper object
    upd_sample_data = SampleInCreate(
        **{**sample.dict(), **{"genome_signature": add_sig_job.id}}
    )
    status = await crud_update_sample(db, upd_sample_data)
    LOG.error(f"status {status}")

    return {
        "id": sample_id,
        "add_signature_job": add_sig_job.id,
        "index_job": index_job.id,
    }


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
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    try:
        status_obj = await update_sample_qc_classification(
            db, sample_id, classification
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return status_obj


@router.post(
    "/samples/{sample_id}/comment",
    response_model=List[CommentInDatabase],
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
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    try:
        comment_obj = await add_comment(db, sample_id, comment)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return comment_obj


@router.delete(
    "/samples/{sample_id}/comment/{comment_id}",
    response_model=List[CommentInDatabase],
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
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Hide comment from sample."""
    try:
        comment_obj = await hide_comment_for_sample(db, sample_id, comment_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return comment_obj


@router.put("/samples/{sample_id}/location", tags=[*DEFAULT_TAGS, "locations"])
async def update_location(
    location_id: str = Body(...),
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    try:
        location_obj: LocationOutputDatabase = await add_location(
            db, sample_id, location_id
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return location_obj


class SimilarSamplesInput(BaseModel):
    """Input parameters for finding similar samples."""

    limit: int | None = Field(default=10, gt=-1, title="Limit the output to x samples")
    similarity: float = Field(default=0.5, gt=0, title="Similarity threshold"),
    cluster: bool = Field(default=False, title="Cluster the similar"),
    typing_method: TypingMethod | None = Field(None, title="Cluster using a specific typing method"),
    cluster_method: ClusterMethod | None = Field(None, title="Cluster the similar"),


@router.post("/samples/{sample_id}/similar", response_model=SubmittedJob, tags=["minhash", *DEFAULT_TAGS])
async def read_sample(
    body: SimilarSamplesInput,
    sample_id: str = Path(
        ...,
        title="ID of the refernece sample",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    LOG.info(f"ref: {sample_id}, body: {body}")
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
