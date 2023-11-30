"""CRUD location operataions."""
from typing import List

from bson import ObjectId

from ..db import Database
from ..models.location import (
    GeoJSONPolygon,
    LocationInputCreate,
    LocationInputDatabase,
    LocationOutputDatabase,
)
from .errors import EntryNotFound


def _document_to_db_obj(document) -> LocationOutputDatabase:
    """Convert a mongodb document to representation of info stored in database."""
    inserted_id = document["_id"]
    return LocationOutputDatabase(
        id=str(inserted_id),
        created_at=ObjectId(inserted_id).generation_time,
        **document,
    )


async def get_locations(
    db: Database, limit: int | None = None, skip: int = 0
) -> List[LocationOutputDatabase]:
    """Get locations from database."""
    cursor = db.location_collection.find({}, skip=skip)
    return [_document_to_db_obj(loc) for loc in await cursor.to_list(limit)]


async def get_location(db: Database, location_id: str) -> LocationOutputDatabase:
    """Get locations from database."""

    doc = await db.location_collection.find_one({"_id": ObjectId(location_id)})
    if doc is None:
        raise EntryNotFound
    # create object representing the dataformat in database
    return _document_to_db_obj(doc)


async def create_location(
    db: Database, location: LocationInputCreate
) -> LocationOutputDatabase:
    """Create a new location"""
    # reformat the data into the database object
    loc_db_fmt = LocationInputDatabase(
        display_name=location.display_name, location={**location.model_dump()}
    )
    # store data in database
    doc = await db.location_collection.insert_one(loc_db_fmt.model_dump())
    # create data representation of inserted object
    inserted_id = doc.inserted_id
    return LocationOutputDatabase(
        id=str(inserted_id),
        created_at=ObjectId(inserted_id).generation_time,
        **loc_db_fmt.model_dump(),
    )


async def get_locations_within_bbox(
    db: Database, bbox: GeoJSONPolygon
) -> List[LocationOutputDatabase]:
    """Query database for locations that are within a given bbox."""
    # read field names from data model
    fields = LocationOutputDatabase.model_fields
    param_location = fields["location"]
    # query database
    cursor = db.location_collection.find(
        {f"{param_location}.coordinates": {"$geoWithin": {"$geometry": bbox.model_dump()}}}
    )
    # convert locations to db representations object
    return [_document_to_db_obj(loc) for loc in await cursor.to_list(None)]
