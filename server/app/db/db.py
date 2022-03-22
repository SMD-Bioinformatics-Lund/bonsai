from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from ..config import DATABASE_NAME
import logging

LOG = logging.getLogger(__name__)


class Database:
    client: AsyncIOMotorClient = None

    def setup(self):
        """setupt collection handler."""
        if self.client is None:
            raise ValueError("Database connection not initialized.")
        # define collection shorthands
        self.db = self.client[DATABASE_NAME]
        self.sample_group_collection: AsyncIOMotorCollection = self.db.sample_group
        self.sample_collection: AsyncIOMotorCollection = self.db.sample
        self.location_collection: AsyncIOMotorCollection = self.db.location
        self.user_collection: AsyncIOMotorCollection = self.db.user


db = Database()
