"""Entrypoints for getting group data."""

from fastapi import APIRouter, Body, Path, status, File, HTTPException
from typing import List
from pymongo.errors import DuplicateKeyError
from ..db import db
from ..models.group import (
    GroupInCreate,
    GroupInfoOut,
    GroupInfoDatabase,
)
from ..crud.group import create_group as create_group_record
from ..crud.group import get_groups, get_group

router = APIRouter()

# , response_model=List[|groupInfoOut]
@router.get("/groups/", response_model=List[GroupInfoDatabase], tags=["groups"])
async def get_groups_in_db():
    """Get information of the number of samples per group loaded into the database."""
    groups = await get_groups(db)
    return groups


@router.post(
    "/groups/",
    response_model=GroupInfoDatabase,
    status_code=status.HTTP_201_CREATED,
)
async def create_group(group_info: GroupInCreate):
    """Create a new group document in the database"""
    # cast input information as group db object
    try:
        result = await create_group_record(db, group_info)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.details["errmsg"],
        )
    return result


@router.get(
    "/groups/{group_id}",
    response_model=GroupInfoDatabase,
    tags=["groups"],
)
async def get_group_in_db(group_id: str):
    """Get information of the number of samples per group loaded into the database."""
    group = await get_group(db, group_id)
    return group


@router.post("/groups/{group_id}/image", status_code=status.HTTP_200_OK)
async def update_image_for_group(group_id: str, image: bytes = File(...)):
    """Add an impage to a group."""
    # cast input information as group db object
    return {"id": group_id, "file_size": len(image)}


@router.put("/groups/{group_id}/sample", status_code=status.HTTP_200_OK)
async def add_sample_to_group(
    sample_id: str,
    group_id: str = Path(..., tilte="The id of the group to get"),
):
    """Add one or more samples to a group"""
    # cast input information as group db object
    # group = await add_sample_to_group(db, sample_id, group_id)
    # return {"id": group_id, "samples": group['addedSamples']}
    return {"group_id": group_id, "sample_id": sample_id}
