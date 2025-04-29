"""Configuration for minhash service"""

from pathlib import Path
from typing import Any
from pydantic import DirectoryPath, PositiveInt
from pydantic_settings import BaseSettings

class RedisConfig(BaseSettings):
    host: str = "redis"
    port: PositiveInt = 6379
    queue: str = "minhash"


class Settings(BaseSettings):
    """Minhash service settings."""

    kmer_size: PositiveInt = 31
    signature_dir: DirectoryPath = Path("/data/signature_db")

    redis: RedisConfig

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