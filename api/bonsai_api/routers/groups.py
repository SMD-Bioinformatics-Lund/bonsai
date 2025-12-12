"""Entrypoints for getting group data."""

import bonsai_api.crud.group as crud_gr
import bonsai_api.crud.memberships as crud_mem
from api_client.audit_log import AuditLogClient
from bonsai_api.crud.errors import DatabaseOperationError, EntryNotFound
from bonsai_api.crud.metadata import get_metadata_fields_for_samples
from bonsai_api.crud.sample import get_samples_summary_v1
from bonsai_api.crud.memberships import get_samples_by_group_ids
from bonsai_api.db import Database
from bonsai_api.dependencies import (
    get_audit_log,
    get_current_active_user,
    get_database,
    get_request_context,
)
from bonsai_api.models.base import MultipleRecordsResponseModel
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.group import (
    DEFAULT_COLUMNS,
    GroupInCreate,
    GroupInfoDatabase,
    SampleTableColumnInput,
    pred_res_cols,
    qc_cols,
)
from bonsai_api.models.memberships import MembershipEdge
from bonsai_api.models.user import UserOutputDatabase
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Security, status
from fastapi.encoders import jsonable_encoder
from pymongo.errors import DuplicateKeyError

from .shared import RouterTags

router = APIRouter()

READ_PERMISSION = "groups:read"
WRITE_PERMISSION = "groups:write"


async def build_column_definitions(
    group_obj: GroupInfoDatabase | None = None,
    include_qc: bool = False,
    include_metadata: bool = False,
    db: Database | None = None,
) -> list[SampleTableColumnInput]:
    """
    Build column definitions for sample table display.

    Args:
        group_obj: Optional group object containing column preferences.
        qc: Whether to use QC columns.
        include_metadata: Whether to include metadata fields.
        db: Database connection, required if include_metadata is True.

    Returns:
        List of SampleTableColumnInput objects.
    """
    base_columns = qc_cols if include_qc else pred_res_cols
    idx_base_cols = {col.id: col for col in base_columns}
    columns: list[SampleTableColumnInput] = []

    if group_obj:
        for col in group_obj.table_columns:
            column_def = idx_base_cols.get(col.id)
            if column_def:
                upd_model = column_def.model_copy(update=col.model_dump())
                columns.append(upd_model)
    else:
        columns = [idx_base_cols[col_id] for col_id in DEFAULT_COLUMNS]

    if include_metadata and db and group_obj:
        # TODO remove additional db query
        edges = await get_samples_by_group_ids([group_obj.group_id], db=db)
        meta_entries = await get_metadata_fields_for_samples(
            db, sample_ids=[e.sample_id for e in edges]
        )
        columns += meta_entries

    return columns


@router.get("/groups/default/columns", tags=[RouterTags.GROUP])
async def get_valid_columns(qc: bool = False):
    """Get group info schema."""
    # get pipeline analysis related columns
    columns = await build_column_definitions(include_qc=qc)
    return jsonable_encoder(columns)


@router.get("/groups/", response_model=list[GroupInfoDatabase], tags=[RouterTags.GROUP])
async def get_groups_in_db(
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Get information of the number of samples per group loaded into the database."""
    groups = await crud_gr.get_groups(db)
    return groups


@router.post(
    "/groups/",
    response_model=GroupInfoDatabase,
    status_code=status.HTTP_201_CREATED,
    tags=[RouterTags.GROUP],
)
async def create_group(
    group_info: GroupInCreate,
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Create a new group document in the database"""
    try:
        result = await crud_gr.create_group(db, group_info, req_ctx, audit_log)
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
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Get information of the number of samples per group loaded into the database."""
    group = await crud_gr.get_group(db, group_id)
    return group


@router.delete(
    "/groups/{group_id}",
    status_code=status.HTTP_200_OK,
    tags=[RouterTags.GROUP],
)
async def delete_group_from_db(
    group_id: str,
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Delete a group from the database."""
    try:
        result = await crud_gr.delete_group(db, group_id, req_ctx, audit_log)
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
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Update information of an group in the database."""
    # cast input information as group db object
    # TODO define which parameters that are allowed to change
    try:
        await crud_gr.update_group(db, group_id, group_info, req_ctx, audit_log)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=404, detail=f"Group with id: {group_id} not in database"
        ) from error
    return {"id": group_id, "group_info": group_info}


@router.put(
    "/groups/{group_id}/samples",
    status_code=status.HTTP_200_OK,
    tags=[RouterTags.GROUP],
    deprecated=True,
)
async def add_samples_to_group(
    group_id: str = Path(..., title="The id of the group to get"),
    sample_ids: list[str] = Query(
        ..., alias="s", title="The ids of the samples to add to the group"
    ),
    db: Database = Depends(get_database),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    audit_log: AuditLogClient = Depends(get_audit_log),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Add one or more samples to a group"""
    # cast input information as group db object
    try:
        # reformat the request to edges and perform mutation
        edges = [
            MembershipEdge(sample_id=sid, group_id=group_id) for sid in sample_ids
        ]
        await crud_mem.add_memberships(edges, db=db)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=sample_ids,
        ) from error
    except DatabaseOperationError as error:
        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED,
            detail=sample_ids,
        ) from error


@router.delete(
    "/groups/{group_id}/samples",
    status_code=status.HTTP_200_OK,
    tags=[RouterTags.GROUP],
)
async def remove_sample_from_group(
    group_id: str = Path(..., title="The id of the group to get"),
    sample_ids: list[str] = Query(
        ..., alias="s", title="The ids of the samples to add to the group"
    ),
    db: Database = Depends(get_database),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    audit_log: AuditLogClient = Depends(get_audit_log),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Add one or more samples to a group"""
    # cast input information as group db object
    try:
        # build edges of the groups to remove
        edges = [
            MembershipEdge(sample_id=sid, group_id=group_id) for sid in sample_ids
        ]
        await crud_mem.remove_memberships(edges, db=db)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=sample_ids,
        ) from error
    except DatabaseOperationError as error:
        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED,
            detail=sample_ids,
        ) from error


@router.get(
    "/groups/{group_id}/columns",
    tags=[RouterTags.GROUP],
)
async def get_columns_for_group(
    group_id: str,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Get information of the number of samples per group loaded into the database."""
    group_obj = GroupInfoDatabase.model_validate(
        await crud_gr.get_group(db, group_id, lookup_samples=False)
    )
    columns = await build_column_definitions(
        group_obj=group_obj, include_metadata=True, db=db
    )
    return columns


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
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Get basic prediction results of all samples in a group."""
    # get group info
    try:
        memberships_edges = await crud_mem.get_samples_by_group_ids([group_id], db=db)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=group_id,
        ) from error
    # query samples
    samples_in_group = [edge.sample_id for edge in memberships_edges]
    db_obj: MultipleRecordsResponseModel = await get_samples_summary_v1(
        db,
        include_samples=samples_in_group,
        limit=limit,
        skip=skip,
        prediction_result=prediction_result,
        qc_metrics=qc_metrics,
    )
    return db_obj
