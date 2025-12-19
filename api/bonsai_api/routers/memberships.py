"""Query and manage many-to-many relationships between samples and groups"""

import logging

from bonsai_api.crud.memberships import (
    get_groups_by_sample_ids,
    get_samples_by_group_ids,
)
from bonsai_api.db import Database
from bonsai_api.dependencies import get_current_active_user, get_database
from bonsai_api.models.memberships import MembershipEdges
from bonsai_api.models.user import UserOutputDatabase
from bonsai_api.routers.shared import RouterTags
from fastapi import APIRouter, Depends, HTTPException, Query, Security, status

LOG = logging.getLogger(__name__)

router = APIRouter()


READ_PERMISSION = "groups:read"
WRITE_PERMISSION = "groups:write"
UPDATE_PERMISSION = "groups:update"


@router.get(
    "/memberships",
    response_model=MembershipEdges,
    tags=[RouterTags.MEM, RouterTags.SAMPLE, RouterTags.GROUP],
)
async def get_group_membership(
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
    sample_ids: list[str] | None = Query(
        None, alias="s", description="Sample IDs to check group membership"
    ),
    group_ids: list[str] | None = Query(
        None, alias="g", description="Check samples that are members of groups with IDs"
    ),
):
    """Get group membership for multiple samples."""
    if sample_ids and group_ids:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="You must provide either sample IDs or group IDs.",
        )

    if not sample_ids and not group_ids:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Neither sample IDs nor group IDs provided.",
        )

    max_ids = 100
    ids = sample_ids or group_ids
    if len(ids) > max_ids:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Too many IDs provided ({len(ids)}). Maximum allowed is {max_ids}.",
        )

    if sample_ids:
        return await get_groups_by_sample_ids(sample_ids, db=db)
    return await get_samples_by_group_ids(group_ids, db=db)
