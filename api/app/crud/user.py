"""User CRUD operations."""
import logging
from typing import List

from fastapi import Depends, HTTPException, Security, status
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBasic, OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt

from ..auth import get_password_hash, verify_password
from ..config import ALGORITHM, SECRET_KEY, USER_ROLES
from ..db import Database, db
from ..models.auth import TokenData
from ..models.user import (
    SampleBasketObject,
    UserInputCreate,
    UserInputDatabase,
    UserOutputDatabase,
)
from .errors import EntryNotFound, UpdateDocumentError

LOG = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", scopes={})


async def get_user(db_obj: Database, username: str) -> UserInputDatabase:
    """Get user from database"""

    users = await get_users(db_obj, usernames=[username])
    if len(users) == 0:
        raise EntryNotFound(username)
    return users[0]


async def get_users(db_obj: Database, usernames: List[str] | None = None) -> List[UserInputDatabase]:
    """Get multiple users by username from database."""
    query = {}
    if usernames is not None:
        query["username"] = {"$in": usernames}

    upd_user_obj = [] 
    async for user in db_obj.user_collection.find(query):
        inserted_id = user["_id"]
        upd_user_obj.append(UserInputDatabase(id=str(inserted_id), **user))
    return upd_user_obj


async def create_user(db_obj: Database, user: UserInputCreate) -> UserOutputDatabase:
    """Create new user in the database."""
    # create hash for password
    hashed_password = get_password_hash(user.password)
    user_db_fmt: UserInputDatabase = UserInputDatabase(
        hashed_password=hashed_password, **user.model_dump()
    )
    # store data in database
    resp_obj = await db.user_collection.insert_one(user_db_fmt.model_dump())
    inserted_id = resp_obj.inserted_id
    user_obj = UserInputDatabase(
        id=str(inserted_id),
        **user_db_fmt.model_dump(),
    )
    return user_obj


async def authenticate_user(db_obj: Database, username: str, password: str) -> bool:
    """Authenticate user login atempt."""
    try:
        user: UserInputDatabase = await get_user(db_obj, username)
    except EntryNotFound:
        return False

    return verify_password(password, user.hashed_password)


async def get_current_user(
    security_scopes: SecurityScopes, token: str = Depends(oauth2_scheme)
) -> UserOutputDatabase:
    """Get current user."""
    if security_scopes.scopes:
        authenticate_value = f"Bearer scope={security_scopes.scope_str}"
    else:
        authenticate_value = "Bearer"

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credentials could not be validated",
        headers={"WWW-Authenticate": authenticate_value},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as error:
        raise credentials_exception from error

    try:
        user: UserOutputDatabase = await get_user(db, username=token_data.username)
    except EntryNotFound as error:
        raise credentials_exception from error
    for scope in security_scopes.scopes:
        users_all_permissions = {
            perm for user_role in user.roles for perm in USER_ROLES.get(user_role, [])
        }
        if not scope in users_all_permissions:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credentials could not be validated",
                headers={"WWW-Authenticate": authenticate_value},
            )
    return user


async def get_current_active_user(
    current_user: UserOutputDatabase = Security(get_current_user, scopes=["users:me"]),
) -> UserOutputDatabase:
    """Get current active user."""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_samples_in_user_basket(
    current_user: UserOutputDatabase = Security(get_current_user, scopes=["users:me"]),
) -> List[SampleBasketObject]:
    """Get samples in the current user basket."""
    user: UserOutputDatabase = await get_user(db, username=current_user.username)
    return user.basket


async def add_samples_to_user_basket(
    current_user: UserOutputDatabase,
    sample_ids: List[SampleBasketObject],
) -> SampleBasketObject:
    """Add samples to the basket of the current user."""
    update_obj = await db.user_collection.update_one(
        {"username": current_user.username},
        {
            "$addToSet": {
                "basket": {
                    "$each": jsonable_encoder(sample_ids, by_alias=False),
                },
            },
        },
    )

    # verify update
    if not update_obj.matched_count == 1:
        raise EntryNotFound(current_user.username)

    if not update_obj.modified_count == 1:
        raise UpdateDocumentError(current_user.username)

    # get updated object
    user: UserOutputDatabase = await get_user(db, username=current_user.username)
    return user.basket


async def remove_samples_from_user_basket(
    current_user: UserOutputDatabase = Security(get_current_user, scopes=["users:me"]),
    sample_ids: List[SampleBasketObject] = [],
) -> SampleBasketObject:
    """Remove samples to the basket of the current user."""
    update_obj = await db.user_collection.update_one(
        {"username": current_user.username},
        {
            "$pull": {
                "basket": {"sample_id": {"$in": sample_ids}},
            },
        },
    )

    # verify update
    if not update_obj.matched_count == 1:
        raise EntryNotFound(current_user.username)

    if not update_obj.modified_count == 1:
        raise UpdateDocumentError(current_user.username)
    # get updated basket
    user: UserOutputDatabase = await get_user(db, username=current_user.username)
    return user.basket
