import logging

from motor.motor_asyncio import AsyncIOMotorClient

from ..config import MAX_CONNECTIONS, MIN_CONNECTIONS, MONGODB_URI
from .db import db


def connect_to_mongo():
    """Setup connection to mongo database."""
    logging.info("Initiate connection to mongo database")
    db.client = AsyncIOMotorClient(
        MONGODB_URI, maxPoolSize=MAX_CONNECTIONS, minPoolSize=MIN_CONNECTIONS
    )
    db.setup()  # initiate collections
    logging.info("Connection successfull")


async def close_mongo_connection():
    """Teardown connection to mongo database."""
    logging.info("Initiate teardown of database connection")
    db.client.close()
    logging.info("Teardown successfull")
