from typing import Dict, List, Annotated

from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Path,
    Query,
    Security,
    status,
    File,
    UploadFile,
)
from pymongo.errors import DuplicateKeyError

from ..crud.sample import EntryNotFound, add_comment, add_location
from ..crud.sample import hide_comment as hide_comment_for_sample
from ..crud.sample import create_sample as create_sample_record
from ..crud.sample import get_sample, get_samples_summary, add_genome_signature_file, update_sample_qc_classification, get_samples_similar_to_reference
from ..crud.sample import update_sample as crud_update_sample
from ..crud.user import get_current_active_user
from ..db import db
from ..models.location import LocationOutputDatabase
from ..models.qc import QcClassification
from ..models.sample import (
    SAMPLE_ID_PATTERN,
    Comment,
    CommentInDatabase,
    SampleInCreate,
    PipelineResult,
)
from ..models.user import UserOutputDatabase
from app import config
import sourmash
from Bio.SeqIO.FastaIO import SimpleFastaParser
import logging
import pathlib
from ..utils import format_error_message

LOG = logging.getLogger(__name__)
router = APIRouter()

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
    #include_cgmlst: bool = Query(True),
    sid: List[str] | None = Query(None),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    # skip and offset function the same
    skip = max([offset, skip])
    db_obj = await get_samples_summary(db, limit=limit, skip=skip, include=sid, include_qc=include_qc, include_mlst=include_mlst)
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

    try:
        signature_path: pathlib.Path = add_genome_signature_file(sample_id, signature)
    except FileExistsError as err:
        raise sig_exist_err
    except Exception as err:
        raise HTTPException(status_code=500, detail=format_error_message(err))
    else:
        # updated sample in database with signature object
        # recast the data to proper object
        upd_sample_data = SampleInCreate(
            **{**sample.dict(), **{"genome_signature": str(signature_path.resolve())}}
        )
        status = await crud_update_sample(db, upd_sample_data)
        LOG.error(f"status {status}")

    # if signature file could not be added to sample db
    if not status:
        # remove added signature file from database and index
        remove_genome_signature_file(sample_id)
        # raise error
        raise HTTPException(
            status=500, detail="The signature file could not be updated"
        )

    return {
        "type": "success",
        "id": sample_id,
        "signature_file": signature_path,
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
        status_obj = await update_sample_qc_classification(db, sample_id, classification)
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


@router.get("/samples/{sample_id}/similar", tags=DEFAULT_TAGS)
async def read_sample(
    sample_id: str = Path(
        ...,
        title="ID of the refernece sample",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    limit: int | None = Query(10, gt=-1, title="Limit the output to x samples"),
    similarity: float = Query(0.5, gt=0, title="Similarity threshold"),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    try:
        samples = get_samples_similar_to_reference(sample_id, kmer_size=config.SIGNATURE_KMER_SIZE, min_similarity=similarity, limit=limit)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        )
    return {"reference": sample_id, "samples": samples, "limit": limit, "simiarity": similarity}
