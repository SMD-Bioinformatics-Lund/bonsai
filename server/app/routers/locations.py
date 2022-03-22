from fastapi import APIRouter, Query, Path, status, HTTPException
from typing import List
from pymongo.errors import DuplicateKeyError

from ..db import db
from ..models.location import LocationInputCreate, LocationOutputDatabase, GeoJSONPolygon
from ..crud.location import create_location as create_location_from_db
from ..crud.location import get_location as get_location_from_db
from ..crud.location import get_locations as get_locations_from_db
from ..crud.location import get_locations_within_bbox
from ..crud.errors import EntryNotFound

router = APIRouter()


@router.get("/locations/")
async def get_locations(limit: int = Query(10, gt=0), skip: int = Query(0, gt=-1)) -> List[LocationOutputDatabase]:
    """Get list of all locations in the database."""
    result = await get_locations_from_db(db, limit, skip)
    return result


@router.post("/locations/")
async def create_location(location: LocationInputCreate) -> LocationOutputDatabase:
    """Create a new location"""
    loc = await create_location_from_db(db, location)
    return loc


@router.get("/locations/bbox")
async def get_location_bbox(left: float, bottom: float, right: float, top: float) -> List[LocationOutputDatabase]:
    """Get a location that are within a bbox."""
    # convert positions to geo json polygon object
    bbox: GeoJSONPolygon = GeoJSONPolygon(coordinates=[[
        (left, top), (left, bottom), (right, bottom), (right, top), (left, top)
    ]])
    # query database
    loc = await get_locations_within_bbox(db, bbox)
    return loc


@router.get("/locations/{location_id}")
async def get_location(location_id: str) -> LocationOutputDatabase:
    """Get location with id"""
    try:
        loc = await get_location_from_db(db, location_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return loc

