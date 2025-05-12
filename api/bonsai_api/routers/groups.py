"""Entrypoints for getting group data."""


import bonsai_api.crud.group as crud_group

from bonsai_api.crud.errors import EntryNotFound, UpdateDocumentError
from bonsai_api.crud.group import create_group as create_group_record
from bonsai_api.crud.group import delete_group, get_group, get_groups, update_group
from bonsai_api.crud.metadata import get_metadata_fields_for_samples
from bonsai_api.crud.sample import get_samples_summary
from bonsai_api.crud.user import get_current_active_user
from bonsai_api.db import Database, get_db
from bonsai_models.models.base import MultipleRecordsResponseModel
from bonsai_models.models.group import (
    GroupInCreate,
    GroupInfoDatabase,
    pred_res_cols,
    qc_cols,
)
from bonsai_models.models.user import UserOutputDatabase
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Security, status
from fastapi.encoders import jsonable_encoder
from pymongo.errors import DuplicateKeyError

from .shared import RouterTags

router = APIRouter()

READ_PERMISSION = "groups:read"
WRITE_PERMISSION = "groups:write"


@router.get("/groups/default/columns", tags=[RouterTags.GROUP])
async def get_valid_columns(qc: bool = False):
    """Get group info schema."""
    # get pipeline analysis related columns
    if qc:
        columns = qc_cols
    else:
        columns = pred_res_cols
    return jsonable_encoder(columns)


@router.get("/groups/", response_model=list[GroupInfoDatabase], tags=[RouterTags.GROUP])
async def get_groups_in_db(
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Get information of the number of samples per group loaded into the database."""
    groups = await get_groups(db)
    return groups


@router.post(
    "/groups/",
    response_model=GroupInfoDatabase,
    status_code=status.HTTP_201_CREATED,
    tags=[RouterTags.GROUP],
)
async def create_group(
    group_info: GroupInCreate,
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Create a new group document in the database"""
    try:
        result = await create_group_record(db, group_info)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.details["errmsg"],
        ) from error
    return result


@router.get(
    "/groups/{group_id}",
    response_model=GroupInfoDatabase,
    tags=[RouterTags.GROUP],
)
async def get_group_in_db(
    group_id: str,
    lookup_samples: bool = False,
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Get information of the number of samples per group loaded into the database."""
    group = await get_group(db, group_id, lookup_samples=lookup_samples)
    return group


@router.delete(
    "/groups/{group_id}",
    status_code=status.HTTP_200_OK,
    tags=[RouterTags.GROUP],
)
async def delete_group_from_db(
    group_id: str,
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Delete a group from the database."""
    try:
        result = await delete_group(db, group_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=404, detail=f"Group with id: {group_id} not in database"
        ) from error
    return result


@router.put(
    "/groups/{group_id}", status_code=status.HTTP_200_OK, tags=[RouterTags.GROUP]
)
async def update_group_info(
    group_id: str,
    group_info: GroupInCreate,
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Update information of an group in the database."""
    # cast input information as group db object
    try:
        await update_group(db, group_id, group_info)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=404, detail=f"Group with id: {group_id} not in database"
        ) from error
    return {"id": group_id, "group_info": group_info}


@router.put(
    "/groups/{group_id}/samples", status_code=status.HTTP_200_OK, tags=[RouterTags.GROUP]
)
async def add_samples_to_group(
    group_id: str = Path(..., title="The id of the group to get"),
    sample_ids: list[str] = Query(..., alias="s", title="The ids of the samples to add to the group"),
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Add one or more samples to a group"""
    # cast input information as group db object
    try:
        await crud_group.add_samples_to_group(db, group_id, sample_ids)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=sample_id,
        ) from error
    except UpdateDocumentError as error:
        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED,
            detail=sample_id,
        ) from error


@router.delete(
    "/groups/{group_id}/samples", status_code=status.HTTP_200_OK, tags=[RouterTags.GROUP]
)
async def remove_sample_from_group(
    group_id: str = Path(..., title="The id of the group to get"),
    sample_ids: list[str] = Query(..., alias="s", title="The ids of the samples to add to the group"),
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Add one or more samples to a group"""
    # cast input information as group db object
    try:
        await crud_group.remove_samples_from_group(db, group_id, sample_ids)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=sample_id,
        ) from error
    except UpdateDocumentError as error:
        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED,
            detail=sample_id,
        ) from error


@router.get(
    "/groups/{group_id}/columns",
    tags=[RouterTags.GROUP],
)
async def get_columns_for_group(
    group_id: str,
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Get information of the number of samples per group loaded into the database."""
    group_obj = GroupInfoDatabase.model_validate(
        await get_group(db, group_id, lookup_samples=False)
    )
    meta_entries = await get_metadata_fields_for_samples(
        db, sample_ids=group_obj.included_samples
    )
    # add default columns
    return pred_res_cols + meta_entries


@router.get(
    "/groups/{group_id}/samples",
    status_code=status.HTTP_200_OK,
    tags=[RouterTags.GROUP],
    response_model=MultipleRecordsResponseModel,
)
async def get_samples_in_group(
    prediction_result: bool = Query(True, description="Include prediction results"),
    qc_metrics: bool = Query(False, description="Include QC metrics"),
    skip: int = 0,
    limit: int = 0,
    group_id: str = Path(..., tilte="The id of the group to get"),
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Get basic prediction results of all samples in a group."""
    # get group info
    try:
        group = await get_group(db, group_id, lookup_samples=False)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=group_id,
        ) from error
    # query samples
    db_obj: MultipleRecordsResponseModel = await get_samples_summary(
        db,
        include_samples=group.included_samples,
        limit=limit,
        skip=skip,
        prediction_result=prediction_result,
        qc_metrics=qc_metrics,
    )
    return db_obj
