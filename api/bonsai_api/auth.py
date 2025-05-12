"""Authentication."""

import random
import string
from datetime import datetime, timedelta
from typing import Any

from bonsai_models.util import get_timestamp
from jose import jwt
from passlib.context import CryptContext

from .config import ALGORITHM, settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_random_pwd(length: int = 15) -> str:
    """Generate a random password with numbers, upper and lower characters."""
    symbols = string.digits + string.ascii_lowercase + string.ascii_uppercase
    return "".join(random.sample(symbols, length))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify if provided passwords are correct"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Get password."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create new access token."""
    to_encode = data.copy()
    if expires_delta:
        expire: datetime = get_timestamp() + expires_delta
    else:
        expire: datetime = get_timestamp() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt
