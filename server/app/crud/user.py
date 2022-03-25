"""User CRUD operations."""
import hashlib

from bson import ObjectId

from ..db import Database
from ..models.user import (UserInputCreate, UserInputDatabase,
                           UserOutputDatabase)
from .errors import EntryNotFound


async def get_user(db: Database, username: str) -> UserOutputDatabase:
    """Get user by username from database."""
    db_obj = await db.user_collection.find_one({"username": username})
    if db_obj is None:
        raise EntryNotFound(f"User {username} not in database")

    inserted_id = db_obj["_id"]
    user_obj = UserInputDatabase(
        id=str(inserted_id), created_at=ObjectId(inserted_id).generation_time, **db_obj
    )
    return user_obj


async def create_user(db: Database, user: UserInputCreate) -> UserOutputDatabase:
    # create hash for password
    hashed_password = hashlib.sha256(user.password.encode()).hexdigest()
    """Create new user in the database."""
    user_db_fmt: UserInputDatabase = UserInputDatabase(
        hashed_password=hashed_password, **user.dict()
    )
    # store data in database
    doc = await db.user_collection.insert_one(user_db_fmt.dict(by_alias=True))
    inserted_id = doc.inserted_id
    db_obj = UserInputDatabase(
        id=str(inserted_id),
        created_at=ObjectId(inserted_id).generation_time,
        **user_db_fmt.dict(by_alias=True),
    )
    return db_obj
