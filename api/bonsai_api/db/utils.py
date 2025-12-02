"""Helper functions for setup and teardown of database connections."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pymongo import AsyncMongoClient

from bonsai_api.config import settings
from .db import MongoDatabase

LOG = logging.getLogger(__name__)

db = MongoDatabase()


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[MongoDatabase, None, None]:
    """Set up database connection."""
    client = AsyncMongoClient(
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
        await db_conn.close()
        LOG.debug("Initiate teardown of database connection")
