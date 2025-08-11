"""Routes for interacting with user data."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Security, status
from pymongo.errors import DuplicateKeyError

from bonsai_api.crud.errors import EntryNotFound, UpdateDocumentError
from bonsai_api.crud.user import (
    add_samples_to_user_basket,
    create_user,
    delete_user,
    get_current_active_user,
    get_user,
    get_users,
    remove_samples_from_user_basket,
    update_user,
)
from bonsai_api.db import Database, get_db
from bonsai_api.models.user import SampleBasketObject, UserInputCreate, UserOutputDatabase

from .shared import RouterTags

LOG = logging.getLogger(__name__)

router = APIRouter()

OWN_USER = "users:me"
READ_PERMISSION = "users:read"
WRITE_PERMISSION = "users:write"


@router.get("/users/me", tags=[RouterTags.USR], response_model=UserOutputDatabase)
async def get_users_me(
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[OWN_USER]
    ),
) -> UserOutputDatabase:
    """Get user data for user with username."""
    return current_user


@router.get("/users/basket", tags=[RouterTags.USR])
async def get_samples_in_basket(
    current_user: Annotated[
        UserOutputDatabase, Security(get_current_active_user, scopes=[OWN_USER])
    ]
) -> list[SampleBasketObject]:
    """Get samples stored in the users sample basket."""
    return current_user.basket


@router.put("/users/basket", tags=[RouterTags.USR])
async def add_samples_to_basket(
    samples: list[SampleBasketObject],
    db: Annotated[Database, Depends(get_db)],
    current_user: Annotated[
        UserOutputDatabase, Security(get_current_active_user, scopes=[OWN_USER])
    ],
) -> list[SampleBasketObject]:
    """Get samples stored in the users sample basket."""
    try:
        basket_obj: list[SampleBasketObject] = await add_samples_to_user_basket(
            current_user, samples, db
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error,
        ) from error
    except UpdateDocumentError as error:
        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED,
            detail=error,
        ) from error
    return basket_obj


@router.delete("/users/basket", tags=[RouterTags.USR])
async def remove_samples_from_basket(
    sample_ids: list[str],
    db: Annotated[Database, Depends(get_db)],
    current_user: Annotated[
        UserOutputDatabase, Security(get_current_active_user, scopes=[OWN_USER])
    ],
) -> list[SampleBasketObject]:
    """Get samples stored in the users sample basket."""
    try:
        basket_obj: list[SampleBasketObject] = await remove_samples_from_user_basket(
            current_user=current_user, sample_ids=sample_ids, db=db
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except UpdateDocumentError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    return basket_obj


@router.get("/users/{username}", tags=[RouterTags.USR])
async def get_user_in_db(
    username: str,
    db: Annotated[Database, Depends(get_db)],
    current_user: Annotated[
        UserOutputDatabase, Security(get_current_active_user, scopes=[READ_PERMISSION])
    ],
) -> UserOutputDatabase:
    """Get user data for user with username."""
    try:
        user = await get_user(db, username=username)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    return user


@router.delete("/users/{username}", tags=[RouterTags.USR])
async def delete_user_from_db(
    username: str,
    db: Annotated[Database, Depends(get_db)],
    current_user: Annotated[
        UserOutputDatabase, Security(get_current_active_user, scopes=[WRITE_PERMISSION])
    ],
):
    """Delete user with username from the database."""
    try:
        user = await delete_user(db, username=username)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
    return user


@router.put("/users/{username}", tags=[RouterTags.USR])
async def update_user_info(
    username: str,
    user: UserInputCreate,
    db: Annotated[Database, Depends(get_db)],
    current_user: Annotated[
        UserOutputDatabase, Security(get_current_active_user, scopes=[WRITE_PERMISSION])
    ],
):
    """Delete user with username from the database."""
    try:
        user = await update_user(db, username=username, user=user)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except Exception as error:
        LOG.error(str(error))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
    return user


@router.get("/users/", status_code=status.HTTP_201_CREATED, tags=[RouterTags.USR])
async def get_users_in_db(
    db: Annotated[Database, Depends(get_db)],
    current_user: Annotated[
        UserOutputDatabase, Security(get_current_active_user, scopes=[READ_PERMISSION])
    ],
) -> list[UserOutputDatabase]:
    """Create a new user."""
    users = await get_users(db)
    return users


@router.post("/users/", status_code=status.HTTP_201_CREATED, tags=[RouterTags.USR])
async def create_user_in_db(
    user: UserInputCreate,
    db: Annotated[Database, Depends(get_db)],
    current_user: Annotated[
        UserOutputDatabase, Security(get_current_active_user, scopes=[WRITE_PERMISSION])
    ],
) -> UserOutputDatabase:
    """Create a new user."""
    try:
        db_obj = await create_user(db, user)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.details["errmsg"],
        ) from error
    return db_obj
