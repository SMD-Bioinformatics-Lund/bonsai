"""Routes for handeling authentication."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..auth import create_access_token
from ..config import settings
from ..crud.user import authenticate_user
from ..db import db
from ..extensions.ldap_extension import ldap_connection

router = APIRouter()

DEFAULT_TAGS = [
    "authentication",
]


@router.post("/token", tags=DEFAULT_TAGS)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Generate a new Oauth2 token."""
    user: bool = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": form_data.username, "scopes": "fool"},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/ldap_token", tags=DEFAULT_TAGS)
async def ldap_login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Generate a new Oauth2 token."""
    # old user authentication
    return {
        "host": settings.ldap_host,
        "use ldap": settings.use_ldap,
        "is_authenticated": ldap_connection.authenticate(
            form_data.username, form_data.password
        ),
        "whoami": ldap_connection.whoami()
    }
    # return {"Auth old method": user, "valid id": is_valid_dn(form_data.username)}
