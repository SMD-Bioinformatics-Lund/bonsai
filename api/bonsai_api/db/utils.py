"""Helper functions for setup and teardown of database connections."""

import logging
from contextlib import contextmanager
from typing import Generator

from motor.motor_asyncio import AsyncIOMotorClient

from ..config import settings
from .db import MongoDatabase

LOG = logging.getLogger(__name__)

db = MongoDatabase()


def get_db() -> Generator[MongoDatabase, None, None]:
    """Set up database connection."""
    db.client = AsyncIOMotorClient(
        settings.mongodb_uri,
        maxPoolSize=settings.max_connections,
        minPoolSize=settings.min_connections,
    )
    try:
        LOG.debug("Setup connection to mongo database")
        db.setup()  # initiate collections
        yield db
    finally:
        # teardown database connection
        db.close()
        LOG.debug("Initiate teardown of database connection")


@contextmanager
def get_db_connection() -> Generator[MongoDatabase, None, None]:
    """Set up database connection."""
    db.client = AsyncIOMotorClient(
        settings.mongodb_uri,
        maxPoolSize=settings.max_connections,
        minPoolSize=settings.min_connections,
    )
    try:
        LOG.debug("Setup connection to mongo database")
        db.setup()  # initiate collections
        yield db
    finally:
        # teardown database connection
        db.close()
        LOG.debug("Initiate teardown of database connection")
