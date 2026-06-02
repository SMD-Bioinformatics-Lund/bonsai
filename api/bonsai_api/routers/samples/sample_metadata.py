"""Metadata, comments, and location management for samples."""

import logging

from api_client.audit_log.client import AuditLogClient
from bonsai_api.crud.metadata import add_metadata_to_sample
from bonsai_api.crud.sample import (
    add_comment,
    add_location,
)
from bonsai_api.crud.sample import hide_comment as hide_comment_for_sample
from bonsai_api.db import Database
from bonsai_api.dependencies import (
    get_audit_log,
    get_current_active_user,
    get_database,
    get_request_context,
)
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.location import LocationOutputDatabase
from bonsai_api.models.metadata import InputMetaEntry
from bonsai_api.models.sample import Comment, CommentInDatabase
from bonsai_api.models.user import UserOutputDatabase
from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    Security,
    status,
)

LOG = logging.getLogger(__name__)
router = APIRouter()

CommentsObj = list[CommentInDatabase]

from .permissions import UPDATE_PERMISSION, WRITE_PERMISSION


@router.post("/samples/{sample_id}/metadata")
async def add_sample_metadata(
    sample_id: str = Path(...),
    metadata: list[InputMetaEntry] = None,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> bool:
    """Add metadata to an existing sample."""
    try:
        resp = await add_metadata_to_sample(
            sample_id=sample_id, metadata=metadata, db=db
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)
        )
    except FileExistsError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err))
    return resp


@router.post(
    "/samples/{sample_id}/comment",
    response_model=CommentsObj,
)
async def post_comment(
    comment: Comment,
    sample_id: str = Path(...),
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> CommentsObj:
    """Add a comment to a sample."""
    return await add_comment(db, sample_id, comment, req_ctx, audit_log)


@router.delete(
    "/samples/{sample_id}/comment/{comment_id}",
)
async def hide_comment(
    sample_id: str = Path(...),
    comment_id: int = Path(..., title="ID of the comment to delete"),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
) -> bool:
    """Hide a comment in a sample from users."""
    return await hide_comment_for_sample(db, sample_id, comment_id, req_ctx, audit_log)


@router.put(
    "/samples/{sample_id}/location",
    response_model=LocationOutputDatabase,
)
async def update_location(
    sample_id: str = Path(...),
    location_id: str = Body(...),
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[UPDATE_PERMISSION]
    ),
) -> LocationOutputDatabase:
    """Update the location of a sample."""
    return await add_location(db, sample_id, location_id)
