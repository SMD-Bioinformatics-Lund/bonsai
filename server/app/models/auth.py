"""Definition of User data models."""

from pydantic import BaseModel
from typing import List


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
    scopes: List[str] = []