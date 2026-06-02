from api_client.audit_log import AuditLogClient
from bonsai_api.db import Database
from bonsai_api.dependencies import (
    get_audit_log,
    get_current_active_user,
    get_database,
    get_request_context,
)
from bonsai_api.exceptions import EntryNotFound
from bonsai_api.models.context import ApiRequestContext
from api.bonsai_api.models.genomic_resource import (
    GenomicResourceCreate,
    GenomicResourceResponse,
)
from bonsai_api.models.user import UserContext, UserOutputDatabase
from api.bonsai_api.services import genomic_resource_service
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Request,
    Security,
    status,
)

from .permissions import READ_PERMISSION, WRITE_PERMISSION

router = APIRouter()

@router.post(
    "/samples/{sample_id}/genomic-resources",
    response_model=list[GenomicResourceResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_genomic_resource(
    payload: GenomicResourceCreate,
    request: Request,
    sample_id: str = Path(..., description="Sample ID"),
    force: bool = False,
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Create a genomic resource set for a sample."""
    return await genomic_resource_service.create_genomic_resource_service(
        db=db,
        sample_id=sample_id,
        force=force,
        request=request,
        resource=payload,
        ctx=req_ctx,
        audit=audit_log,
    )


@router.get(
    "/genomic-resources/{resource_id}",
    response_model=GenomicResourceResponse,
)
async def get_genomic_resource(
    resource_id: str,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Fetch a genomic resource by ID."""
    return await genomic_resource_service.get_genomic_resource_service(
        db,
        resource_id=resource_id,
    )


@router.get(
    "/samples/{sample_id}/resources",
    response_model=list[GenomicResourceResponse],
)
async def list_genomic_resources_for_sample(
    sample_id: str,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """List all genomic resources associated with a sample."""
    user = UserContext(
        user_id=current_user.username,
        roles=current_user.roles,
    )
    return await genomic_resource_service.list_genomic_resources_for_sample_service(
        db=db,
        sample_id=sample_id,
    )


@router.delete(
    "/genomic-resources/{resource_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_genomic_resource(
    resource_id: str,
    db: Database = Depends(get_database),
    audit_log: AuditLogClient = Depends(get_audit_log),
    req_ctx: ApiRequestContext = Depends(get_request_context),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Delete a genomic resource."""
    try:
        user = UserContext(
            user_id=current_user.username,
            roles=current_user.roles,
        )
        return await genomic_resource_service.delete_genomic_resource_service(
            db=db,
            resource_id=resource_id,
            ctx=req_ctx,
            audit=audit_log,
            user=user,
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
