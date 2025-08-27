"""Configuration for minhash service"""

from enum import StrEnum
import tempfile
from pathlib import Path
from typing import Any
from copy import deepcopy
from logging import config as logging_config

from pydantic import ConfigDict, DirectoryPath, Field, PositiveInt, field_validator
from pydantic_settings import BaseSettings


def _get_trash_dir() -> Path:
    """Create a temporary directory for trash."""
    return Path(tempfile.mkdtemp(prefix="minhash_trash_"))


class LogLevel(StrEnum):
    """Log level options."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


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


class BasePeriodicTaskConfig(BaseSettings):
    """Generic configuration for periodic integrity check task."""

    endabled: bool = True  # enable/disable background task processing
    cron: str = "0 12 * * SAT"  # cron schedule for periodic tasks
    queue: str = "minhash"  # redis queue name for periodic tasks


class PeriodicIntegrityCheckConfig(BasePeriodicTaskConfig):
    """Configure scheudling of background tasks."""

    model_config = ConfigDict(env_prefix="integrity_task_")

    cron: str = "0 12 * * SAT"  # cron schedule for periodic tasks


class CleanupRemovedFilesConfig(BasePeriodicTaskConfig):
    """Configure scheudling of background tasks."""

    model_config = ConfigDict(env_prefix="purge_files_task_")

    cron: str = "0 * * * *"  # cron schedule for periodic tasks


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
    # periodic tasks
    periodic_integrity_check: PeriodicIntegrityCheckConfig = PeriodicIntegrityCheckConfig()
    cleanup_removed_files: CleanupRemovedFilesConfig = CleanupRemovedFilesConfig()

    log_level: LogLevel = LogLevel.INFO

    @field_validator("trash_dir", mode="before")
    @classmethod
    def ensure_trash_dir_exists(cls, v):
        """Ensure that the trash directory exists."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    def build_logging_conffig(self) -> dict[str, Any]:
        """Build logging configuration dictionary."""
        log_config = deepcopy(LOG_CONFIG)
        # update log levels
        log_config["handlers"]["default"]["level"] = self.log_level.value
        log_config["loggers"]["root"]["level"] = self.log_level.value
        return log_config


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

def configure_logging(cnf: Settings) -> None:
    """Configure logging from settings."""
    logging_config.dictConfig(cnf.build_logging_conffig())


settings = Settings()
