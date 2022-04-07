"""Authentication."""
from datetime import datetime, timedelta
from http.client import HTTPException

from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import ALGORITHM, SECRET_KEY
from .crud.user import EntryNotFound, get_user
from .db import Database
from .models.auth import TokenData
from .models.user import UserInputDatabase, UserOutputDatabase

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify if provided passwords are correct"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Get password."""
    return pwd_context.hash(password)


def authenticate_user(db: Database, username: str, password: str) -> bool:
    """Authenticate user login atempt."""
    try:
        user: UserInputDatabase = get_user(db, username)
    except EntryNotFound:
        return False

    if not verify_password(password, user.hashed_password):
        return False
    return True


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create new access token."""
    to_encode: dict = data.copy()
    if expires_delta:
        expire: datetime = datetime.utcnow() + expires_delta
    else:
        expire: datetime = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    db: Database, token: str = Depends(oauth2_scheme)
) -> UserOutputDatabase:
    """Get current user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credentials could not be validated",
        headers={"WWW-Authenticate": "Bearer"},
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
    return user


async def get_current_active_user(
    current_user: UserOutputDatabase = Depends(get_current_user),
) -> UserOutputDatabase:
    """Get current active user."""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
