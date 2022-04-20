from datetime import datetime
from typing import Dict, List, Union

from fastapi import (APIRouter, Body, HTTPException, Path, Query, Security,
                     status)
from pymongo.errors import DuplicateKeyError

from ..crud.sample import EntryNotFound, add_comment, add_location
from ..crud.sample import create_sample as create_sample_record
from ..crud.sample import get_sample, get_samples
from ..crud.user import get_current_active_user
from ..db import db
from ..models.location import LocationOutputDatabase
from ..models.sample import (SAMPLE_ID_PATTERN, Comment, CommentInDatabase,
                             SampleInCreate, SampleInDatabase,
                             SampleInPipelineInput)
from ..models.user import UserOutputDatabase

router = APIRouter()

DEFAULT_TAGS = [
    "samples",
]
READ_PERMISSION = "samples:read"
WRITE_PERMISSION = "samples:write"


@router.get("/samples/", tags=DEFAULT_TAGS)
async def read_samples(
    limit: int = Query(10, gt=0),
    skip: int = Query(0, gt=-1),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    db_obj = await get_samples(db, limit, skip)
    return db_obj


@router.post("/samples/", status_code=status.HTTP_201_CREATED, tags=DEFAULT_TAGS)
async def create_sample(
    sample: SampleInPipelineInput,
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
    return db_obj


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
    sample: Dict | SampleInPipelineInput = Body({}),
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
