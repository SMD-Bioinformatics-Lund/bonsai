"""Manage connections to mongo client."""

import logging
from typing import Any

from fastapi import Request
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from .core.config import Settings

LOG = logging.getLogger(__name__)


def get_mongo_connection(settings: Settings) -> MongoClient[Any]:
    """Get mongodb client."""

    LOG.info("Creating MongoClient", extra={"appname": settings.service_name})
    client: MongoClient[Any] = MongoClient(
        settings.mongo.uri, appname=settings.service_name
    )

    # test if client is reachable
    try:
        client.admin.command("ping")
    except PyMongoError:
        LOG.error("MongoDb is not reachable (uri: %s)", settings.mongo.uri)
        client.close()  # ensure closed on failure
        raise

    return client


def get_db_client(request: Request) -> MongoClient:
    """Get database client instance from app state."""
    db = request.app.state.database
    if db is None:
        raise RuntimeError("Database not instanciated!")
    return db


def get_database(request: Request, settings: Settings) -> Database[Any]:
    """Get database"""
    db_name: str = settings.mongo.database
    return get_db_client(request).get_database(db_name)


def get_collection(request: Request, settings: Settings) -> Collection[Any]:
    """Get audit log collection."""
    col_name: str = settings.mongo.collection
    return get_database(request, settings).get_collection(col_name)
