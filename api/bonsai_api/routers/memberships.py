"""Query and manage many-to-many relationships between samples and groups"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status

from bonsai_api.db import Database
from bonsai_api.dependencies import get_current_active_user, get_database
from bonsai_api.routers.shared import RouterTags
from bonsai_api.crud.memberships import get_samples_group_membership
from bonsai_api.models.memberships import MembershipsQueryResponse
from bonsai_api.models.user import UserOutputDatabase

LOG = logging.getLogger(__name__)

router = APIRouter()


READ_PERMISSION = "groups:read"
WRITE_PERMISSION = "groups:write"
UPDATE_PERMISSION = "groups:update"


@router.get(
    "/memberships",
    response_model=MembershipsQueryResponse,
    tags=[RouterTags.SAMPLE, RouterTags.GROUP],
)
async def get_group_membership(
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
    sids: list[str] = Query(
        None, description="Sample IDs to check group membership"
    ),
    gids: list[str] = Query(
        None, description="Check samples that are members of groups with IDs"
    ),
):
    """Get group membership for multiple samples."""
    if sids and gids:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="You must provide either sample IDs or group IDs."
        )

    if not sids and not gids:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Neither sample IDs nor group IDs provided."
        )

    max_ids = 100
    if len(sids) > max_ids:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Too many IDs provided ({len(sids)}). Maximum allowed is {max_ids}.",
        )

    memberships = await get_samples_group_membership(db, sids)
    return memberships
