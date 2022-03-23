from fastapi import APIRouter, Query, Path, status, HTTPException, Body
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, List, Union
from pymongo.errors import DuplicateKeyError

from ..models.location import LocationOutputDatabase

from ..db import db
from ..crud.sample import EntryNotFound, create_sample as create_sample_record
from ..crud.sample import get_samples, get_sample, add_comment, add_location

from ..models.sample import (
    SampleInPipelineInput,
    SampleInDatabase,
    SampleInCreate,
    Comment,
    SAMPLE_ID_PATTERN,
)

router = APIRouter()


@router.get("/samples/", tags=["samples"])
async def read_samples(limit: int = Query(10, gt=0), skip: int = Query(0, gt=-1)):
    return get_samples(limit, skip)


@router.post("/samples/", status_code=status.HTTP_201_CREATED)
async def create_sample(sample: SampleInPipelineInput):
    try:
        db_obj = await create_sample_record(db, sample)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.details["errmsg"],
        )
    return db_obj


@router.get("/samples/{sample_id}")
async def read_sample(
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    )
):
    try:
        sample_obj = await get_sample(db, sample_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return sample_obj


@router.put("/samples/{sample_id}")
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


@router.post("/samples/{sample_id}/comment")
async def post_comment(
    comment: Comment,
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
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


@router.put("/samples/{sample_id}/location")
async def update_location(
    location_id: str = Body(...),
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
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
