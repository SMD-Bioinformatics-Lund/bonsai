"""Helper functions for setup and teardown of database connections."""
import logging

from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import contextmanager

from ..config import settings
from .db import MongoDatabase

LOG = logging.getLogger(__name__)

db = MongoDatabase()


@contextmanager
def get_db() -> MongoDatabase:
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
        db.client.close()
        LOG.debug("Initiate teardown of database connection")
