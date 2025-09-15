"""Manage connections to mongo client."""

import logging
from typing import Any
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from .core.config import Settings

LOG = logging.getLogger(__name__)


_client: MongoClient[Any] | None = None


def get_mongo_client(settings: Settings) -> MongoClient[Any]:
    """Get mongodb client."""
    global _client
    if _client is not None:
        return _client
    
    LOG.info("Creating MongoClient", extra={"appname": settings.service_name})
    client: MongoClient[Any] = MongoClient(settings.mongo.uri, appname=settings.service_name)

    # test if client is reachable
    try:
        client.admin.command("ping")
    except PyMongoError:
        LOG.error("MongoDb is not reachable (uri: %s)", settings.mongo.uri)
        try:
            client.close()  # ensure closed on failure
        except Exception as exc:
            LOG.error("An error occured when trying to close mongo connection: %s", exc)
        raise

    _client = client
    return client


def get_database(settings: Settings) -> Database[Any]:
    """Get database"""
    db_name: str = settings.mongo.database
    return get_mongo_client(settings).get_database(db_name)


def get_collection(settings: Settings) -> Collection[Any]:
    """Get audit log collection."""
    col_name: str = settings.mongo.collection
    return get_database(settings).get_collection(col_name)


def close_mongo_client():
    """Close the mongodb connection."""
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception as exc:
            LOG.error("An error occured when trying to close mongo connection: %s", exc)
        finally:
            _client = None