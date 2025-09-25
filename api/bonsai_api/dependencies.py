"""API functions that are used as dependencies."""

import logging
from typing import Annotated, Generator
from fastapi import Depends, Request, Security, HTTPException
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from fastapi.security import SecurityScopes
from bonsai_api.crud.user import get_user_by_token
from bonsai_api.config import settings

from bonsai_api.db.db import MongoDatabase
from bonsai_api.models.user import UserOutputDatabase
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.db import Database

from api_client.audit_log import AuditLogClient
from api_client.audit_log.models import Actor, SourceType

LOG = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", scopes={})


def get_audit_log(request: Request) -> AuditLogClient | None:
    """Get audit log instance from API state.
    
    Return None if audit log has not been setup"""
    if hasattr(request.app.state, "audit_log"):
        return request.app.state.audit_log
    LOG.debug("Audit Log has not been configured")


def get_database(request: Request) -> Generator[MongoDatabase, None, None]:
    """Get database connection."""
    if not hasattr(request.app.state, "db"):
        raise RuntimeError("The database was not found in application state.")
    return request.app.state.db
    

async def get_current_user(
        security_scopes: SecurityScopes,
        token: Annotated[str, Depends(oauth2_scheme)],
        db: Database = Depends(get_database),
        ):
    """Look up logged in user from token."""

    return await get_user_by_token(security_scopes, token, db)


async def get_current_active_user(
    current_user: UserOutputDatabase = Security(get_current_user, scopes=["users:me"]),
) -> UserOutputDatabase | None:
    """Get current active user."""
    # disable API authentication
    if not settings.api_authentication:
        return None

    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_request_context(request: Request, user: UserOutputDatabase | None = Depends(get_current_active_user)):
    """Get the context of a request."""
    req_id = request.headers.get("X-Request-ID")
    client_ip = request.client.host if request.client else None
    username = user.username if user is not None else None
    actor_id: str = username or client_ip or "unknown"

    # build meta
    meta = {"request_id": req_id}
    if client_ip:
        meta["client_ip"] = client_ip

    return ApiRequestContext(
        actor = Actor(type=SourceType.USR, id=actor_id),
        metadata = meta
    )