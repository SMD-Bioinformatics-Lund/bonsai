"""Routes for interacting with user data."""

from datetime import datetime
from typing import Dict, List, Union

from fastapi import APIRouter, HTTPException, Security, status
from pymongo.errors import DuplicateKeyError

from ..crud.errors import EntryNotFound, UpdateDocumentError
from ..crud.user import (add_samples_to_user_basket, create_user,
                         get_current_active_user, get_samples_in_user_basket,
                         get_user, remove_samples_from_user_basket)
from ..db import db
from ..models.user import (SampleBasketObject, UserInputCreate,
                           UserOutputDatabase)

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


@router.get("/users/basket", tags=DEFAULT_TAGS)
async def get_samples_in_basket(
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[OWN_USER]
    )
) -> List[SampleBasketObject]:
    """Get samples stored in the users sample basket."""
    basket_obj: List[SampleBasketObject] = await get_samples_in_user_basket(
        current_user
    )
    return basket_obj


@router.put("/users/basket", tags=DEFAULT_TAGS)
async def add_samples_to_basket(
    samples: List[SampleBasketObject],
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[OWN_USER]
    ),
) -> List[SampleBasketObject]:
    """Get samples stored in the users sample basket."""
    try:
        basket_obj: List[SampleBasketObject] = await add_samples_to_user_basket(
            current_user, samples
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    except UpdateDocumentError as error:
        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED,
            detail=str(error),
        )
    return basket_obj


@router.delete("/users/basket", tags=DEFAULT_TAGS)
async def remove_samples_from_basket(
    sample_ids: List[str],
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[OWN_USER]
    ),
) -> List[SampleBasketObject]:
    """Get samples stored in the users sample basket."""
    try:
        basket_obj: List[SampleBasketObject] = await remove_samples_from_user_basket(
            current_user, sample_ids
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    except UpdateDocumentError as error:
        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED,
            detail=str(error),
        )
    return basket_obj


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
