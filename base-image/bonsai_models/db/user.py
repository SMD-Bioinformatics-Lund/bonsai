"""This module defines the UserInDb model that defines user infromation stored in the database."""
import datetime
from pydantic import Field

from bonsai_models.schema.user import UserBase
from bonsai_models.utils.timestamp import get_timestamp


class UserInDb(UserBase):  # pylint: disable=too-few-public-methods
    """User data to be written to database.

    Includes modified timestamp.
    """

    hashed_password: str
    modified_at: datetime.datetime = Field(default_factory=get_timestamp)
