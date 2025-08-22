""""Manages mongo database connections."""

from typing import Any
from pymongo import MongoClient
from pymongo.database import Database

class MongoDB:
    """Container for mongo databases."""

    _client: MongoClient[Any] | None = None
    _db: Database[Any] | None = None

    @classmethod
    def get_db(cls) -> Database[Any]:
        """Get connection to client."""
        if cls._db is None:
            raise RuntimeError("MongoDB not initialized. Call setup() first.")
        return cls._db

    @classmethod
    def setup(cls, host: str, port: int, db_name: str):
        """Setup database connection."""
        if isinstance(cls._client, MongoClient):
            raise RuntimeError("Database connection already instanciated, there can only be one connection.")

        cls._client = MongoClient(host=host, port=port)
        cls._db = cls._client.get_database(db_name)
