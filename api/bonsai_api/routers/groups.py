"""Entrypoints for getting group data."""

from api.bonsai_api.services.group_service import build_column_overrides
from bonsai_api.crud.builder.summary_manifest import MANIFEST
import bonsai_api.crud.group as crud_gr
import bonsai_api.services.group_service as service_gr
import bonsai_api.services.membership_service as service_mem
from api_client.audit_log import AuditLogClient
from bonsai_api.exceptions import DatabaseOperationError, EntryNotFound
from bonsai_api.db import Database
from bonsai_api.dependencies import (get_audit_log, get_current_active_user,
                                     get_database, get_request_context)
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.group import (GroupAllowedUpdate, GroupInfoCreate,
                                     GroupInfoOut, GroupListResponse,
                                     GroupPresetIn, GroupUpdate)
from bonsai_api.models.memberships import MembershipEdge
from bonsai_api.models.user import UserContext, UserOutputDatabase
from bonsai_api.services import group_service
from fastapi import (APIRouter, Depends, HTTPException, Path, Query, Security,
                     status)
from pymongo.errors import DuplicateKeyError

from .shared import RouterTags

router = APIRouter()

READ_PERMISSION = "groups:read"
WRITE_PERMISSION = "groups:write"


@router.get("/groups/", 
            response_model=GroupListResponse, 
            response_model_by_alias=False,
            tags=[RouterTags.GROUP])
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
    response_model=GroupInfoOut,
    status_code=status.HTTP_201_CREATED,
    tags=[RouterTags.GROUP],
)
async def create_group(
    group_info: GroupInfoCreate,
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Create a new group document in the database"""
    try:
        usr = UserContext(user_id=current_user.username, roles=current_user.roles)
        result = await group_service.create_group_service(
            db,
            group_record=group_info,
            ctx=req_ctx,
            audit=audit_log,
            creator=usr,
        )
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.details["errmsg"],
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from error
    return result


@router.get(
    "/groups/{group_id}",
    response_model=GroupInfoOut,
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
    try:
        group = await crud_gr.get_group(db, group_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=group_id,
        ) from error
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
        user = UserContext(user_id=current_user.username, roles=current_user.roles)
        result = await service_gr.delete_group_service(db, group_id=group_id, ctx=req_ctx, user=user, audit=audit_log)
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
    group_info: GroupUpdate,
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Update mutable group core fields (display name, description)."""
    try:
        result = await crud_gr.update_group_core(
            db, group_id, group_info, req_ctx, audit_log
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=404, detail=f"Group with id: {group_id} not in database"
        ) from error
    return result


@router.put(
    "/groups/{group_id}/allowed_columns",
    status_code=status.HTTP_200_OK,
    tags=[RouterTags.GROUP],
)
async def set_allowed_columns_for_group(
    group_id: str,
    payload: GroupAllowedUpdate,
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Set allowed table columns for a group."""
    try:
        updated = await crud_gr.set_allowed_columns(
            db, group_id, payload, req_ctx, audit_log
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=404, detail=f"Group with id: {group_id} not in database"
        ) from error
    return updated


@router.post(
    "/groups/{group_id}/presets",
    status_code=status.HTTP_201_CREATED,
    tags=[RouterTags.GROUP],
)
async def upsert_preset_for_group(
    group_id: str,
    preset: GroupPresetIn,
    set_default: bool = Query(
        False, alias="default", description="Set this preset as default"
    ),
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Create or update a preset for a group."""
    try:
        updated = await crud_gr.upsert_preset(
            db, group_id, preset, set_default, req_ctx, audit_log
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=404, detail=f"Group with id: {group_id} not in database"
        ) from error
    return updated


@router.delete(
    "/groups/{group_id}/presets/{preset_id}",
    status_code=status.HTTP_200_OK,
    tags=[RouterTags.GROUP],
)
async def delete_preset_from_group(
    group_id: str,
    preset_id: str,
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Delete a preset from a group."""
    try:
        updated = await crud_gr.delete_preset(
            db, group_id, preset_id, req_ctx, audit_log
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=404, detail=f"Group with id: {group_id} not in database"
        ) from error
    return updated


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
        edges = [MembershipEdge(sample_id=sid, group_id=group_id) for sid in sample_ids]
        await service_mem.add_memberships(edges, db=db)
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
        edges = [MembershipEdge(sample_id=sid, group_id=group_id) for sid in sample_ids]
        await service_mem.remove_memberships(edges, db=db)
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
    group_obj = await crud_gr.get_group(db, group_id)
    columns = await build_column_overrides(
        group_obj=group_obj, manifest=MANIFEST 
    )
    return columns
