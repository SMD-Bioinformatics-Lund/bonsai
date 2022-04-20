"""User CRUD operations."""
from email.policy import HTTP
from gzip import READ
from http.client import HTTPException
from bson import ObjectId
from fastapi import Depends, status, Security
from fastapi.security import (HTTPBasic, HTTPBasicCredentials, SecurityScopes,
                              OAuth2PasswordBearer)
from jose import JWTError, jwt

from ..auth import get_password_hash, verify_password
from ..db import Database, db
from ..models.auth import TokenData
from ..models.user import (UserInputCreate, UserInputDatabase,
                           UserOutputDatabase)
from .errors import EntryNotFound
from ..config import USER_ROLES

security = HTTPBasic()
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={}
)

def get_current_user_ldap(credentials: HTTPBasicCredentials = Depends(security)):
    """Get current user from LDAP3 server."""
    pass


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
    hashed_password = get_password_hash(user.password)
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


async def authenticate_user(db: Database, username: str, password: str) -> bool:
    """Authenticate user login atempt."""
    try:
        user: UserInputDatabase = await get_user(db, username)
    except EntryNotFound:
        return False

    if not verify_password(password, user.hashed_password):
        return False
    return True


async def get_current_user(
    security_scopes: SecurityScopes, 
    token: str = Depends(oauth2_scheme)
) -> UserOutputDatabase:
    """Get current user."""
    if security_scopes.scopes:
        authenticate_value = f"Bearer scope={security_scopes.scope_str}"
    else:
        authenticate_value = f"Bearer"
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
    except JWTError:
        raise credentials_exception
    try:
        user: UserOutputDatabase = get_user(db, username=token_data.username)
    except EntryNotFound:
        raise credentials_exception
    for scope in security_scopes.scopes:
        if scope not in USER_ROLES.get(user.roles, []):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credentials could not be validated",
                headers={"WWW-Authenticate": authenticate_value},
            )
    return user


async def get_current_active_user(
    current_user: UserOutputDatabase = Security(get_current_user, scopes=["me"]),
) -> UserOutputDatabase:
    """Get current active user."""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user