"""Routes for handeling authentication."""

from datetime import datetime, timedelta
from http.client import HTTPException

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from ..auth import create_access_token
from ..config import ACCESS_TOKEN_EXPIRE_MINUTES
from ..crud.user import authenticate_user
from ..db import db

router = APIRouter()

DEFAULT_TAGS = [
    "authentication",
]


@router.post("/token", tags=DEFAULT_TAGS)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Generate a new Oauth2 token."""
    user: bool = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username, "scopes": "fool"},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}
