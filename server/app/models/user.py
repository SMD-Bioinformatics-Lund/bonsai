"""Definition of User data models."""

from .base import DBModelMixin, ModifiedAtRWModel, RWModel
from pydantic import EmailStr, Field


class UserBase(RWModel):
    """Base user model"""

    username: str
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")
    email: EmailStr
    disabled: bool = False


class UserInputCreate(UserBase):
    """
    User data sent over API.
    """

    password: str


class UserInputDatabase(UserBase, ModifiedAtRWModel):
    """User data to be written to database.

    Includes modified timestamp.
    """

    hashed_password: str = Field(..., alias="hashedPassword")


class UserOutputDatabase(UserBase, DBModelMixin):
    """Representation of the userdata in the database.

    Information returned by API.
    """

    pass
