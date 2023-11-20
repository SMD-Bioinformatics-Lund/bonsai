"""Routers for reading or manipulating locations."""
from typing import List

from fastapi import APIRouter, HTTPException, Query, Security, status

from ..crud.errors import EntryNotFound
from ..crud.location import create_location as create_location_from_db
from ..crud.location import get_location as get_location_from_db
from ..crud.location import get_locations as get_locations_from_db
from ..crud.location import get_locations_within_bbox
from ..crud.user import get_current_active_user
from ..db import db
from ..models.location import (
    GeoJSONPolygon,
    LocationInputCreate,
    LocationOutputDatabase,
)
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
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
) -> List[LocationOutputDatabase]:
    """Entrypoint for listing all locations in the database.

    :param limit: Limit result to N locations, defaults to Query(10, gt=0)
    :type limit: int, optional
    :param skip: Skip the N first locations, defaults to Query(0, gt=-1)
    :type skip: int, optional
    :param current_user: for authentication, defaults to Security
    :type current_user: UserOutputDatabase, optional
    :return: Locations in the database.
    :rtype: List[LocationOutputDatabase]
    """
    result = await get_locations_from_db(db, limit, skip)
    return result


@router.post("/locations/", tags=DEFAULT_TAGS)
async def create_location(
    location: LocationInputCreate,
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
) -> LocationOutputDatabase:
    """Entrypoint for creating a new location in the database.

    :param location: Location information
    :type location: LocationInputCreate
    :param current_user: for authentication, defaults to Security
    :type current_user: UserOutputDatabase, optional
    :return: Location object in the database.
    :rtype: LocationOutputDatabase
    """
    loc = await create_location_from_db(db, location)
    return loc


@router.get("/locations/bbox", tags=DEFAULT_TAGS)
async def get_location_bbox(
    left: float,
    bottom: float,
    right: float,
    top: float,
    current_user: UserOutputDatabase = Security( # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
) -> List[LocationOutputDatabase]:
    """Get locations within a bbox.

    :param left: bbox left GPS point
    :type left: float
    :param bottom: bbox bottom GPS point
    :type bottom: float
    :param right: bbox right GPS point
    :type right: float
    :param top: bbox top GPS point
    :type top: float
    :param current_user: for authentication, defaults to Security
    :type current_user: UserOutputDatabase, optional
    :return: Locations within bbox
    :rtype: List[LocationOutputDatabase]
    """
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
    current_user: UserOutputDatabase = Security( # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
) -> LocationOutputDatabase:
    """Get location with id.

    :param location_id: Location id
    :type location_id: str
    :param current_user: for authentication, defaults to Security
    :type current_user: UserOutputDatabase, optional
    :raises HTTPException: Returns 404 error if location is not in the database.
    :return: Location info
    :rtype: LocationOutputDatabase
    """
    try:
        loc = await get_location_from_db(db, location_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error,
        ) from error
    return loc
