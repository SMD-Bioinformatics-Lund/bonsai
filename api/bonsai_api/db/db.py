"""Code for setting up a database connection."""

import logging

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.collection import AsyncCollection

LOG = logging.getLogger(__name__)


class MongoDatabase:  # pylint: disable=too-few-public-methods
    """Container for database connection and collections."""

    def __init__(self) -> None:
        """Constructor function."""
        self.client: AsyncMongoClient | None = None
        self.db: AsyncDatabase | None = None
        self.sample_group_collection: AsyncCollection | None = None
        self.sample_collection: AsyncCollection | None = None
        self.location_collection: AsyncCollection | None = None
        self.user_collection: AsyncCollection | None = None

    def setup(self, client: AsyncMongoClient, db_name: str = "bonsai"):
        """Setup collection handler."""
        self.client = client
        # define collection shorthands
        self.db = self.client.get_database(db_name)
        self.sample_group_collection = self.db.get_collection("sample_group")
        self.sample_collection = self.db.get_collection("sample")
        self.location_collection = self.db.get_collection("location")
        self.user_collection = self.db.get_collection("user")

    async def close(self) -> None:
        """Close database connection."""
        if isinstance(self.client, AsyncMongoClient):
            await self.client.close()
        else:
            raise RuntimeError("Trying to close an uninstantiated database")


def setup_db_connection(uri: str, db_name: str) -> MongoDatabase:
    """Setup connection"""
    mongo_conn = AsyncMongoClient(uri)
    db = MongoDatabase()
    db.setup(mongo_conn, db_name=db_name)
    return db
