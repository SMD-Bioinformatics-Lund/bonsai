"""Definition of User data models."""

from typing import List

from pydantic import EmailStr

from ..config import settings
from .base import DBModelMixin, ModifiedAtRWModel, RWModel


class SampleBasketObject(RWModel):  # pylint: disable=too-few-public-methods
    """Contaner for sample baskt content."""

    sample_id: str
    assay: str


class UserBase(RWModel):  # pylint: disable=too-few-public-methods
    """Base user model"""

    username: str
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr
    disabled: bool = False
    roles: List[str] = []
    basket: List[SampleBasketObject] = []


class UserInputCreate(UserBase):  # pylint: disable=too-few-public-methods
    """
    User data sent over API.
    """

    password: str


class UserInputDatabase(
    UserBase, ModifiedAtRWModel
):  # pylint: disable=too-few-public-methods
    """User data to be written to database.

    Includes modified timestamp.
    """

    hashed_password: str


class UserOutputDatabase(
    UserBase, DBModelMixin
):  # pylint: disable=too-few-public-methods
    """Representation of the userdata in the database.

    Information returned by API.
    """

    authentication_method: str = "ldap" if settings.use_ldap_auth else "simple"
