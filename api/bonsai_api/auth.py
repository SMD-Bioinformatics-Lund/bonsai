"""Authentication."""

import random
import string
from datetime import datetime, timedelta

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


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create new access token."""
    to_encode: dict = data.copy()
    if expires_delta:
        expire: datetime = datetime.utcnow() + expires_delta
    else:
        expire: datetime = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt
