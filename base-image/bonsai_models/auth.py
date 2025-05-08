"""Definition of User data models."""

from typing import List

from pydantic import BaseModel


class Token(BaseModel):  # pylint: disable=too-few-public-methods
    """Authentication token data model."""

    access_token: str
    token_type: str


class TokenData(BaseModel):  # pylint: disable=too-few-public-methods
    """Token data model."""

    username: str | None = None
    scopes: List[str] = []
