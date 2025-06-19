"""Definition of User data models."""

import datetime
from pydantic import EmailStr, Field

from bonsai_models.utils.timestamp import get_timestamp
from bonsai_models.base import ApiModel


class UserBase(ApiModel):
    """Base user model"""

    username: str
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr
    disabled: bool = False
    roles: list[str] = []


class UserCreate(UserBase):
    """
    User data sent over API.
    """

    password: str


class UserResponse(UserBase):
    """Representation of the userdata in the database.

    Information returned by API.
    """

    authentication_method: str = "simple"
    created_at: datetime.datetime = Field(default_factory=get_timestamp)
    modified_at: datetime.datetime = Field(default_factory=get_timestamp)
