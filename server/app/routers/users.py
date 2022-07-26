"""Routes for interacting with user data."""

from datetime import datetime
from typing import Dict, List, Union

from fastapi import APIRouter, HTTPException, Path, Query, Security, status
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from ..crud.errors import EntryNotFound
from ..crud.sample import create_sample as create_sample_record
from ..crud.user import create_user, get_current_active_user, get_user
from ..db import db
from ..models.user import UserInputCreate, UserInputDatabase, UserOutputDatabase

router = APIRouter()

DEFAULT_TAGS = [
    "users",
]
OWN_USER = "users:me"
READ_PERMISSION = "users:read"
WRITE_PERMISSION = "users:write"


@router.get("/users/me", tags=DEFAULT_TAGS, response_model=UserOutputDatabase)
async def get_users_me(
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[OWN_USER]
    ),
) -> UserOutputDatabase:
    """Get user data for user with username."""
    return current_user


@router.get("/users/{username}", tags=DEFAULT_TAGS)
async def get_user_in_db(
    username: str,
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
) -> UserOutputDatabase:
    """Get user data for user with username."""
    try:
        user = await get_user(db, username=username)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return user


@router.post("/users/", status_code=status.HTTP_201_CREATED, tags=DEFAULT_TAGS)
async def create_user_in_db(
    user: UserInputCreate,
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
) -> UserOutputDatabase:
    """Create a new user."""
    try:
        db_obj = await create_user(db, user)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.details["errmsg"],
        )
    return db_obj
