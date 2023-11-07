from typing import List

from fastapi import APIRouter, HTTPException, Path, Query, Security, status
from pymongo.errors import DuplicateKeyError

from ..crud.errors import EntryNotFound
from ..crud.location import create_location as create_location_from_db
from ..crud.location import get_location as get_location_from_db
from ..crud.location import get_locations as get_locations_from_db
from ..crud.location import get_locations_within_bbox
from ..crud.user import get_current_active_user
from ..db import db
from ..models.location import (GeoJSONPolygon, LocationInputCreate,
                               LocationOutputDatabase)
from ..models.user import UserOutputDatabase

router = APIRouter()

DEFAULT_TAGS = [
    "locations",
]
READ_PERMISSION = "locations:read"
WRITE_PERMISSION = "locations:write"


@router.get("/locations/", tags=DEFAULT_TAGS)
async def get_locations(
    limit: int = Query(10, gt=0),
    skip: int = Query(0, gt=-1),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
) -> List[LocationOutputDatabase]:
    """Get list of all locations in the database."""
    result = await get_locations_from_db(db, limit, skip)
    return result


@router.post("/locations/", tags=DEFAULT_TAGS)
async def create_location(
    location: LocationInputCreate,
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
) -> LocationOutputDatabase:
    """Create a new location"""
    loc = await create_location_from_db(db, location)
    return loc


@router.get("/locations/bbox", tags=DEFAULT_TAGS)
async def get_location_bbox(
    left: float,
    bottom: float,
    right: float,
    top: float,
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
) -> List[LocationOutputDatabase]:
    """Get a location that are within a bbox."""
    # convert positions to geo json polygon object
    bbox: GeoJSONPolygon = GeoJSONPolygon(
        coordinates=[
            [(left, top), (left, bottom), (right, bottom), (right, top), (left, top)]
        ]
    )
    # query database
    loc = await get_locations_within_bbox(db, bbox)
    return loc


@router.get("/locations/{location_id}", tags=DEFAULT_TAGS)
async def get_location(
    location_id: str,
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
) -> LocationOutputDatabase:
    """Get location with id"""
    try:
        loc = await get_location_from_db(db, location_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return loc
