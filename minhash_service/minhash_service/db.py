"""Interface for the minhash service database operations."""

import logging
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

LOG = logging.getLogger(__name__)

class MongoDB:
    """Database interface for the minhash service."""

    def __init__(self, host: str, port: int, database_name: str):
        """Initialize the MongoDB client."""
        self.host = host
        self.port = port
        self.database_name = database_name

        self.client: MongoClient | None = None
        self.db: Database | None = None
        self.minhash_collection: Collection | None = None
    
    def __enter__(self):
        """Enter the context manager and connect to the database."""
        self.client = MongoClient(self.host, self.port)
        self.db = self.client[self.database_name]
        self.minhash_collection = self.db["signatures"]

        LOG.info("MongoDB connection established.")
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager and close the database connection."""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            self.minhash_collection = None
            LOG.info("MongoDB connection closed.")