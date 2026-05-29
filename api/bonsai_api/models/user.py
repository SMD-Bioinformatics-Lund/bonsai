"""Definition of User data models."""

from bonsai_api.config import settings
from pydantic import EmailStr

from .base import UUIDModelMixin, ForbidExtraModelMixin, RWModel, Timestamps


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
    roles: list[str] = []
    basket: list[SampleBasketObject] = []


class UserInputCreate(UserBase):  # pylint: disable=too-few-public-methods
    """
    User data sent over API.
    """

    password: str


class UserInputDatabase(UserBase, Timestamps):  # pylint: disable=too-few-public-methods
    """User data to be written to database.

    Includes modified timestamp.
    """

    hashed_password: str


class UserOutputDatabase(
    UserBase, UUIDModelMixin
):  # pylint: disable=too-few-public-methods
    """Representation of the userdata in the database.

    Information returned by API.
    """

    authentication_method: str = "ldap" if settings.use_ldap_auth else "simple"


class UserContext(ForbidExtraModelMixin):
    """Minimal user context information stored in request."""

    user_id: str | None
    roles: list[str] | None = None

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.roles is not None and "admin" in self.roles
