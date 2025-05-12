"""Routes for handeling authentication."""

from datetime import timedelta

from bonsai_api.auth import create_access_token
from bonsai_api.config import settings
from bonsai_api.crud.user import authenticate_user
from bonsai_api.db import Database, get_db
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from .shared import RouterTags

router = APIRouter()


@router.post("/token", tags=[RouterTags.AUTH])
async def login_for_access_token(
    db: Database = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """Generate a new Oauth2 token."""
    is_authenticated: bool = await authenticate_user(
        db, form_data.username, form_data.password
    )
    if not is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": form_data.username, "scopes": "default"},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}
