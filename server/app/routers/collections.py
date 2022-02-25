"""Entrypoints for getting collections data."""

from fastapi import APIRouter, Query, Path, status, File, HTTPException
from typing import List
from pymongo.errors import DuplicateKeyError
from ..db import db
from ..models.collection import (
    CollectionInCreate,
    CollectionInfoOut,
    CollectionInfoDatabase,
)
from ..crud.collection import create_collection as create_collection_record
from ..crud.collection import get_collections, get_collection

router = APIRouter()

# , response_model=List[|collectionInfoOut]
@router.get(
    "/collections/", response_model=List[CollectionInfoDatabase], tags=["collections"]
)
async def get_collections_in_db():
    """Get information of the number of samples per collection loaded into the database."""
    collections = await get_collections(db)
    return collections


@router.post(
    "/collections/",
    response_model=CollectionInfoDatabase,
    status_code=status.HTTP_201_CREATED,
)
async def create_collection(collection_info: CollectionInCreate):
    """Create a new collection document in the database"""
    # cast input information as collection db object
    try:
        result = await create_collection_record(db, collection_info)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.details["errmsg"],
        )
    return result


@router.get(
    "/collections/{collection_id}",
    response_model=CollectionInfoDatabase,
    tags=["collections"],
)
async def get_collection_in_db(collection_id: str):
    """Get information of the number of samples per collection loaded into the database."""
    collection = await get_collection(db, collection_id)
    return collection


@router.post("/collections/{tax_id}/image", status_code=status.HTTP_200_OK)
async def update_image_for_collection(tax_id: str, image: bytes = File(...)):
    """Create a new collection document in the database"""
    # cast input information as collection db object
    return {"id": tax_id, "file_size": len(image)}
