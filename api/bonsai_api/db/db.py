"""Code for setting up a database connection."""

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from ..config import settings

LOG = logging.getLogger(__name__)


class MongoDatabase:  # pylint: disable=too-few-public-methods
    """Container for database connection and collections."""

    def __init__(self) -> None:
        """Constructor function."""
        self.client: AsyncIOMotorClient | None = None
        self.db = None
        self.sample_group_collection: AsyncIOMotorCollection | None = None
        self.sample_collection: AsyncIOMotorCollection | None = None
        self.location_collection: AsyncIOMotorCollection | None = None
        self.user_collection: AsyncIOMotorCollection | None = None

    def setup(self):
        """setupt collection handler."""
        if self.client is None:
            raise ValueError("Database connection not initialized.")
        # define collection shorthands
        self.db = self.client[settings.database_name]
        self.sample_group_collection: AsyncIOMotorCollection = self.db.sample_group
        self.sample_collection: AsyncIOMotorCollection = self.db.sample
        self.location_collection: AsyncIOMotorCollection = self.db.location
        self.user_collection: AsyncIOMotorCollection = self.db.user

    def close(self) -> None:
        """Close database connection."""
        if isinstance(self.client, AsyncIOMotorClient):
            self.client.close()
        else:
            raise ValueError("Trying to close an uninstantiated database")
