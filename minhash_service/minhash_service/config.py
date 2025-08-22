"""Configuration for minhash service"""

from pathlib import Path
from typing import Any
from pydantic import PositiveInt, ConfigDict
from pydantic_settings import BaseSettings

class MongodbConfig(BaseSettings):
    """MongoDB configuration for minhash service."""

    model_config = ConfigDict(env_prefix="mongodb_")
    
    host: str = "mongodb"
    port: PositiveInt = 27017
    database: str = "minhash_db"
    collection: str = "signatures"


class RedisConfig(BaseSettings):
    model_config = ConfigDict(env_prefix="redis_")

    host: str = "redis"
    port: PositiveInt = 6379
    queue: str = "minhash"

class Settings(BaseSettings):
    """Minhash service settings."""

    kmer_size: PositiveInt = 31
    signature_dir: Path = Path("/data/signature_db")
    index_name: str = "genomes"

    redis: RedisConfig = RedisConfig()
    mongodb: MongodbConfig = MongodbConfig()

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