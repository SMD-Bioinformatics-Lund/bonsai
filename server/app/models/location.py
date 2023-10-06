from typing import List, Tuple

from pydantic import BaseModel, Field, validator

from .base import DBModelMixin, ModifiedAtRWModel

COORDS = Tuple[float, float]


def check_coordinates_polygon(coords: List[COORDS]) -> COORDS:
    """Check that polygon coordinates are valid."""
    for outer_coords in coords:
        for inner_coords in outer_coords:
            check_coordinates(inner_coords)
    return coords


def check_coordinates(coords: COORDS) -> COORDS:
    """Check that coordinates are valid."""
    long, lat = coords
    if not (-180 < long < 180):
        raise ValueError(f"Invalid longitude coordinate {long}")
    if not (-90 < lat < 90):
        raise ValueError(f"Invalid latitude coordinate {lat}")
    return coords


class GeoJSONPoint(BaseModel):
    type: str = "Point"
    coordinates: COORDS

    # validators
    _validate_coords = validator("coordinates", allow_reuse=True)(check_coordinates)


class GeoJSONPolygon(BaseModel):
    type: str = "Polygon"

    coordinates: List[List[COORDS]]

    # validators
    _validate_coords = validator("coordinates", allow_reuse=True)(
        check_coordinates_polygon
    )

    @validator("coordinates")
    def check_closed_polygon(cls, coords):
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


class LocationBase(ModifiedAtRWModel):
    """Contianer for geo locations, based on GeoJSON format."""

    display_name: str = Field(..., min_length=0, alias="displayName")
    disabled: bool = False


class LocationInputCreate(LocationBase):
    """Contianer for geo locations, based on GeoJSON format."""

    coordinates: Tuple[float, float]

    # validators
    _validate_coords = validator("coordinates", allow_reuse=True)(check_coordinates)


class LocationInputDatabase(LocationBase):
    """Contianer for geo locations, based on GeoJSON format."""

    location: GeoJSONPoint = Field(..., alias="geoLocation")


class LocationOutputDatabase(LocationInputDatabase, DBModelMixin):
    """Contianer for geo locations, based on GeoJSON format."""

    pass
