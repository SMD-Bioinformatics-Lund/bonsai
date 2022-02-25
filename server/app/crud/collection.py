"""Functions for conducting CURD operations on collections collection"""
import logging
from bson.objectid import ObjectId
from ..db import Database
from ..models.collection import CollectionInCreate, CollectionInfoDatabase
from typing import Dict, Any, List

LOG = logging.getLogger(__name__)


def collection_document_to_db_object(
    document: Dict[str, Any]
) -> CollectionInfoDatabase:
    """Convert document from database to CollectionInfoDatabase object."""
    inserted_id = document["_id"]
    db_obj = CollectionInfoDatabase(
        id=str(inserted_id),
        created_at=ObjectId(inserted_id).generation_time,
        modified_at=ObjectId(inserted_id).generation_time,
        **document
    )
    return db_obj


async def get_collections(db: Database) -> List[CollectionInfoDatabase]:
    """Get collections from database."""
    cursor = db.sample_group_collection.find({})
    collections = []
    for row in await cursor.to_list(length=100):
        collections.append(collection_document_to_db_object(row))
    return collections


async def get_collection(db: Database, collection_id: str) -> CollectionInfoDatabase:
    """Get collections from database."""
    collection = await db.sample_group_collection.find_one(
        {"collectionId": collection_id}
    )
    return collection_document_to_db_object(collection)


async def create_collection(
    db: Database, collection_record: CollectionInCreate
) -> CollectionInfoDatabase:
    """Create a new collection document."""
    # cast input data as the type expected to insert in the database
    doc = await db.sample_group_collection.insert_one(
        collection_record.dict(by_alias=True)
    )
    inserted_id = doc.inserted_id
    db_obj = CollectionInfoDatabase(
        id=str(inserted_id),
        created_at=ObjectId(inserted_id).generation_time,
        modified_at=ObjectId(inserted_id).generation_time,
        **collection_record.dict(by_alias=True)
    )
    return db_obj


async def update_image(
    db: Database, image: CollectionInCreate
) -> CollectionInfoDatabase:
    """Create a new collection document."""
    # cast input data as the type expected to insert in the database
    db_obj = await db.sample_group_collection.insert_one(
        collection_record.dict(by_alias=True)
    )
    return db_obj
