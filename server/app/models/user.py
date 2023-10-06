"""Definition of User data models."""

from typing import List

from pydantic import EmailStr

from .base import DBModelMixin, ModifiedAtRWModel, RWModel


class SampleBasketObject(RWModel):
    """Contaner for sample baskt content."""

    sample_id: str
    analysis_profile: str


class UserBase(RWModel):
    """Base user model"""

    username: str
    first_name: str
    last_name: str
    email: EmailStr
    disabled: bool = False
    roles: List[str] = []
    basket: List[SampleBasketObject] = []


class UserInputCreate(UserBase):
    """
    User data sent over API.
    """

    password: str


class UserInputDatabase(UserBase, ModifiedAtRWModel):
    """User data to be written to database.

    Includes modified timestamp.
    """

    hashed_password: str


class UserOutputDatabase(UserBase, DBModelMixin):
    """Representation of the userdata in the database.

    Information returned by API.
    """

    pass
