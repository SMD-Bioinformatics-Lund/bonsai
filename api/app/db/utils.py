"""Helper functions for setup and teardown of database connections."""
import logging

from motor.motor_asyncio import AsyncIOMotorClient

from ..config import settings
from .db import db

LOG = logging.getLogger(__name__)


def connect_to_mongo():
    """Setup connection to mongo database."""
    LOG.info("Initiate connection to mongo database")
    db.client = AsyncIOMotorClient(
        settings.mongodb_uri, maxPoolSize=settings.max_connections, minPoolSize=settings.min_connections
    )
    db.setup()  # initiate collections
    LOG.info("Connection successfull")


async def close_mongo_connection():
    """Teardown connection to mongo database."""
    LOG.info("Initiate teardown of database connection")
    db.client.close()
    LOG.info("Teardown successfull")
