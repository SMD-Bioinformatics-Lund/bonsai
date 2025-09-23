"""User CRUD operations."""

import logging
from typing import Any

from fastapi.encoders import jsonable_encoder

import bonsai_api
from api_client.audit_log import AuditLogClient, EventCreate
from api_client.audit_log.models import SourceType, Subject, EventSeverity
from bonsai_api.dependencies import ApiRequestContext
from bonsai_api.auth import get_password_hash, verify_password
from bonsai_api.config import settings
from bonsai_api.db import Database
from bonsai_api.extensions.ldap_extension import ldap_connection
from bonsai_api.models.user import (
    SampleBasketObject,
    UserInputCreate,
    UserInputDatabase,
    UserOutputDatabase,
)
from .errors import EntryNotFound, UpdateDocumentError

LOG = logging.getLogger(__name__)


async def get_user(db_obj: Database, username: str) -> UserInputDatabase:
    """Get user from database"""

    users = await get_users(db_obj, usernames=[username])
    if len(users) == 0:
        raise EntryNotFound(username)
    return users[0]


async def delete_user(db_obj: Database, username: str, ctx: ApiRequestContext, audit: AuditLogClient | None = None):
    """Delete user from the database"""
    resp = await db_obj.user_collection.delete_one({"username": username})
    exc: Exception | None = None
    if resp.deleted_count == 0:
        exc = EntryNotFound(username)

    if isinstance(audit, AuditLogClient):
        # prepare event metadata and submit event
        event_subject = Subject(id=username, type=SourceType.SYS)

        meta: dict[str, Any] = ctx.metadata
        severity = EventSeverity.INFO
        if exc is not None:
            meta['exception'] = exc
            severity = EventSeverity.ERROR

        event = EventCreate(
            source_service=bonsai_api.__name__, event_type="delete_user", 
            severity=severity, actor=ctx.actor, subject=event_subject, metadata=ctx.metadata)
        audit.post_event(event)
    
    if exc is not None:
        raise exc
    return username


async def update_user(db_obj: Database, username: str, user: UserInputCreate, 
                      ctx: ApiRequestContext, audit: AuditLogClient | None = None):
    """Delete user from the database"""
    # get old user object
    new_user_info = user.model_dump()
    if len(user.password) > 0:
        # create hash for new password
        LOG.info("Changed password for %s", username)
        new_user_info["hashed_password"] = get_password_hash(user.password)

    user_in_db = await get_user(db_obj, username=username)
    # update changed fields in created user object
    upd_user_info = user_in_db.model_copy(update=new_user_info)
    resp = await db_obj.user_collection.replace_one(
        {"username": username}, upd_user_info.model_dump()
    )
    exc: Exception | None = None
    if resp.matched_count == 0:
        exc = EntryNotFound(username)
    if resp.modified_count == 0:
        exc = UpdateDocumentError(username)

    if isinstance(audit, AuditLogClient):
        # prepare event metadata and submit event
        event_subject = Subject(id=username, type=SourceType.SYS)

        meta: dict[str, Any] = ctx.metadata
        severity = EventSeverity.INFO
        if exc is not None:
            meta['exception'] = exc
            severity = EventSeverity.ERROR

        event = EventCreate(
            source_service=bonsai_api.__name__, event_type="update_user", 
            severity=severity, actor=ctx.actor, subject=event_subject, metadata=ctx.metadata)
        audit.post_event(event)


async def create_user(db_obj: Database, user: UserInputCreate, ctx: ApiRequestContext, audit: AuditLogClient | None = None) -> UserOutputDatabase:
    """Create new user in the database."""
    # create hash for password
    hashed_password = get_password_hash(user.password)
    user_db_fmt: UserInputDatabase = UserInputDatabase(
        hashed_password=hashed_password, **user.model_dump()
    )
    # store data in database
    resp_obj = await db_obj.user_collection.insert_one(user_db_fmt.model_dump())
    inserted_id = resp_obj.inserted_id
    user_obj = UserInputDatabase(
        id=str(inserted_id),
        **user_db_fmt.model_dump(),
    )
    if isinstance(audit, AuditLogClient):
        event_subject = Subject(id=user_obj.username, type=SourceType.USR)
        event = EventCreate(
            source_service=bonsai_api.__name__, event_type="create_user", 
            actor=ctx.actor, subject=event_subject, metadata=ctx.metadata)
        audit.post_event(event)
    return user_obj


async def get_users(
    db_obj: Database, usernames: list[str] | None = None
) -> list[UserInputDatabase]:
    """Get multiple users by username from database."""
    query = {}
    if usernames is not None:
        query["username"] = {"$in": usernames}

    upd_user_obj = []
    async for user in db_obj.user_collection.find(query):
        inserted_id = user["_id"]
        upd_user_obj.append(UserInputDatabase(id=str(inserted_id), **user))
    return upd_user_obj


async def authenticate_user(db_obj: Database, username: str, password: str) -> bool:
    """Authenticate user login atempt."""
    try:
        user: UserInputDatabase = await get_user(db_obj, username)
    except EntryNotFound:
        return False

    # use authenticate users with an LDAP server
    if settings.use_ldap_auth:
        is_authenticated = ldap_connection.authenticate(username, password)
    else:
        # use username and password to authenticate users
        is_authenticated = verify_password(password, user.hashed_password)
    return is_authenticated


async def get_samples_in_user_basket(
    db: Database,
    current_user: UserOutputDatabase,
) -> list[SampleBasketObject]:
    """Get samples in the current user basket."""
    user: UserOutputDatabase = await get_user(db, username=current_user.username)
    return user.basket


async def add_samples_to_user_basket(
    current_user: UserOutputDatabase,
    sample_ids: list[SampleBasketObject],
    db: Database,
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
    sample_ids: list[SampleBasketObject],
    db: Database,
    current_user: UserOutputDatabase,
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
        sample_ids_in_basket = await db.user_collection.find_one(
            {"username": current_user.username}, {"basket": 1}
        )
        LOG.error(
            "try removing samples %s from basket. Content: %s",
            sample_ids,
            sample_ids_in_basket,
        )
        raise UpdateDocumentError(
            f"Error when updating the basket of {current_user.username}"
        )
    # get updated basket
    user: UserOutputDatabase = await get_user(db, username=current_user.username)
    return user.basket
