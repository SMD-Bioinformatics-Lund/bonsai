"""Helper functions for setup and teardown of database connections."""

import logging
from contextlib import contextmanager
from typing import Generator

from motor.motor_asyncio import AsyncIOMotorClient

from ..config import settings
from .db import MongoDatabase

LOG = logging.getLogger(__name__)

db = MongoDatabase()

@contextmanager
def get_db_connection() -> Generator[MongoDatabase, None, None]:
    """Set up database connection."""
    client = AsyncIOMotorClient(
        settings.mongodb_uri,
        maxPoolSize=settings.max_connections,
        minPoolSize=settings.min_connections,
    )
    db_conn = MongoDatabase()
    try:
        LOG.debug("Setup connection to mongo database")
        db_conn.setup(client, settings.database_name)  # initiate collections
        yield db_conn
    finally:
        # teardown database connection
        db_conn.close()
        LOG.debug("Initiate teardown of database connection")
