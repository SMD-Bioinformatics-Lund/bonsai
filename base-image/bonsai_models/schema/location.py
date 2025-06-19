"""Data modules for location information."""

import datetime
from pydantic import BaseModel, Field, field_validator

from bonsai_models.utils.timestamp import get_timestamp
from bonsai_models.base import ApiModel

Position = tuple[float, float]


def validate_coordinates(coords: Position) -> Position:
    """Check that coordinates are valid."""
    long, lat = coords
    if not -180 < long < 180:
        raise ValueError(f"Invalid longitude coordinate {long}")
    if not -90 < lat < 90:
        raise ValueError(f"Invalid latitude coordinate {lat}")
    return coords


class GeoCoordinate(BaseModel):
    """Container of coordinates."""

    coordinates: Position

    # validators
    @field_validator("coordinates")
    @classmethod
    def check_coordinates(cls, coords: Position) -> Position:
        """Check that coordinates are valid."""
        return validate_coordinates(coords)


def check_coordinates_polygon(coords: list[list[Position]]) -> list[list[Position]]:
    """Check that polygon coordinates are valid."""
    for outer_coords in coords:
        for inner_coords in outer_coords:
            validate_coordinates(inner_coords)
    return coords


class GeoJSONPoint(GeoCoordinate):  # pylint: disable=too-few-public-methods
    """Container of a GeoJSON representation of a point."""

    type: str = "Point"


class GeoJSONPolygon(BaseModel):
    """Container of a GeoJSON representation of a polygon."""

    type: str = "Polygon"

    coordinates: list[list[Position]]

    @field_validator("coordinates")
    @classmethod
    def check_closed_polygon(
        cls, coords
    ):  # pylint: disable=no-self-argument
        """Verify that polygon is closed."""

        base_message = "Invalid Polygon GeoJSON object"
        for poly_obj in coords:
            if len(poly_obj) < 4:
                raise ValueError(
                    f"{base_message}: has only {len(poly_obj)} points, min 3"
                )

            if not poly_obj[0] == poly_obj[-1]:
                raise ValueError(f"{base_message}: object is not closed.")
        return coords


class LocationBase(ApiModel):
    """Contianer for geo locations, based on GeoJSON format."""

    display_name: str = Field(..., min_length=0, alias="displayName")
    disabled: bool = False


class LocationCreate(GeoCoordinate):
    """Contianer for geo locations, based on GeoJSON format."""


class LocationResponse(LocationBase):
    """Return basic geolocation information."""

    created_at: datetime.datetime = Field(default_factory=get_timestamp)
    modified_at: datetime.datetime = Field(default_factory=get_timestamp)
