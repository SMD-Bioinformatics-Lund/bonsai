"""Configuration for minhash service"""

import tempfile
from pathlib import Path
from typing import Any

from pydantic import ConfigDict, DirectoryPath, Field, PositiveInt, field_validator
from pydantic_settings import BaseSettings


def _get_trash_dir() -> Path:
    """Create a temporary directory for trash."""
    return Path(tempfile.mkdtemp(prefix="minhash_trash_"))


class MongodbConfig(BaseSettings):
    """MongoDB configuration for minhash service."""

    model_config = ConfigDict(env_prefix="mongodb_")

    host: str = "mongodb"
    port: PositiveInt = 27017
    database: str = "minhash_db"
    collection: str = "signatures"
    log_collection: str = "logs"


class RedisConfig(BaseSettings):
    """Redis configuration for minhash service."""

    model_config = ConfigDict(env_prefix="redis_")

    host: str = "redis"
    port: PositiveInt = 6379
    queue: str = "minhash"


class Settings(BaseSettings):
    """Minhash service settings."""

    kmer_size: PositiveInt = 31
    signature_dir: Path = Path("/data/signature_db")
    index_name: str = "genomes"
    trash_dir: DirectoryPath = Field(
        default_factory=_get_trash_dir, description="Directory for trashed files"
    )

    redis: RedisConfig = RedisConfig()
    mongodb: MongodbConfig = MongodbConfig()

    @field_validator("trash_dir", mode="before")
    @classmethod
    def ensure_trash_dir_exists(cls, v):
        """Ensure that the trash directory exists."""
        v.mkdir(parents=True, exist_ok=True)
        return v


# Logging configuration
LOG_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "default": {
            "level": "DEBUG",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",  # Default is stderr
        },
    },
    "loggers": {
        "root": {  # root logger
            "handlers": ["default"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}


settings = Settings()
