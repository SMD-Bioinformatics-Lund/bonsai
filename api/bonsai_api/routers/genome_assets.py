
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Security,
    status,
)

from api.bonsai_api.exceptions import EntryNotFound
from bonsai_api.models.genome_asset import GenomicAssetCreate, GenomicAssetOut, GenomicAssetListResponse
from api_client.audit_log import AuditLogClient
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.user import UserContext, UserOutputDatabase
from bonsai_api.services import genome_asset_service

from bonsai_api.db import Database
from bonsai_api.dependencies import (
    get_audit_log,
    get_current_active_user,
    get_database,
    get_request_context,
)

from .tags import RouterTags


router = APIRouter(tags=[RouterTags.GENOMIC_ASSET])

READ_PERMISSION = "genomic_assets:read"
WRITE_PERMISSION = "genomic_assets:write"


@router.post(
    "/samples/{sample_id}/genomic-assets",
    response_model=GenomicAssetOut,
    status_code=status.HTTP_201_CREATED,
    tags=[RouterTags.SAMPLE],
)
async def create_genomic_asset(
    payload: GenomicAssetCreate,
    sample_id: str = Path(..., description="Sample ID"),
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Create a genomic asset set for a sample."""
    try:
        user = UserContext(
            user_id=current_user.username,
            roles=current_user.roles,
        )
        return await genomic_asset_service.create_genomic_asset_service(
            db=db,
            sample_id=sample_id,
            payload=payload,
            ctx=req_ctx,
            audit=audit_log,
            creator=user,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

@router.get(
    "/genomic-assets/{asset_id}",
    response_model=GenomicAssetOut,
)
async def get_genomic_asset(
    asset_id: str,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Fetch a genomic asset by ID."""
    try:
        return await genomic_asset_service.get_genomic_asset_service(
            db=db,
            asset_id=asset_id,
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.get(
    "/samples/{sample_id}/genomic-assets",
    response_model=GenomicAssetListResponse,
    tags=[RouterTags.SAMPLE],
)
async def list_genomic_assets_for_sample(
    sample_id: str,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """List all genomic assets associated with a sample."""
    user = UserContext(
        user_id=current_user.username,
        roles=current_user.roles,
    )
    return await genomic_asset_service.list_genomic_assets_for_sample_service(
        db=db,
        sample_id=sample_id,
        user=user,
    )
    

@router.delete(
    "/genomic-assets/{asset_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_genomic_asset(
    asset_id: str,
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Delete a genomic asset."""
    try:
        user = UserContext(
            user_id=current_user.username,
            roles=current_user.roles,
        )
        return await genomic_asset_service.delete_genomic_asset_service(
            db=db,
            asset_id=asset_id,
            ctx=req_ctx,
            audit=audit_log,
            user=user,
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error