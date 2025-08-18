"""
This module defines the `LocationInDb` class, a Pydantic model for representing
geographical locations in the database using the GeoJSON format.

Classes:
    LocationInDb: Inherits from `LocationBase` and includes fields for a GeoJSON
        point (`location`), creation timestamp (`created_at`), and modification
        timestamp (`modified_at`). Timestamps are automatically set using the
        `get_timestamp` utility.
"""
import datetime
from pydantic import Field

from bonsai_models.schema.location import GeoJSONPoint, LocationBase
from bonsai_models.utils.timestamp import get_timestamp


class LocationInDb(LocationBase):  # pylint: disable=too-few-public-methods
    """Contianer for geo locations, based on GeoJSON format."""

    location: GeoJSONPoint
    created_at: datetime.datetime = Field(default_factory=get_timestamp)
    modified_at: datetime.datetime = Field(default_factory=get_timestamp)
