"""Routes for interacting with user data."""

from datetime import datetime
from typing import Dict, List, Union

from fastapi import APIRouter, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from ..crud.errors import EntryNotFound
from ..crud.sample import create_sample as create_sample_record
from ..crud.user import create_user, get_user
from ..db import db
from ..models.user import UserInputCreate, UserOutputDatabase

router = APIRouter()


@router.get("/users/{username}")
async def get_user_in_db(username: str) -> UserOutputDatabase:
    """Get user data for user with username."""
    try:
        user = await get_user(db, username=username)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return user


@router.post("/users/", status_code=status.HTTP_201_CREATED)
async def create_user_in_db(user: UserInputCreate) -> UserOutputDatabase:
    """Create a new user."""
    try:
        db_obj = await create_user(db, user)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.details["errmsg"],
        )
    return db_obj
