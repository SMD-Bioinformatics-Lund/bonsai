"""Configuration for minhash service"""

import tempfile
from copy import deepcopy
from enum import StrEnum
from logging import config as logging_config
from pathlib import Path
from typing import Any

from pydantic import (DirectoryPath, Field, HttpUrl, PositiveInt,
                      ValidationError, computed_field, field_validator,
                      model_validator)
from pydantic_settings import BaseSettings, SettingsConfigDict

from minhash_service.signatures.models import IndexFormat


def _get_trash_dir() -> Path:
    """Create a temporary directory for trash."""
    return Path(tempfile.mkdtemp(prefix="minhash_trash_"))


class IntegrityReportLevel(StrEnum):
    """Options what to notify."""

    NEVER = "NEVER"
    WARNING = "WARNING"
    ERROR = "ERROR"


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
    signature_collection: str = "signatures"
    report_collection: str = "report"
    audit_trail_collection: str = "audit_trail"


class RedisConfig(BaseSettings):
    """Redis configuration for minhash service."""

    model_config = SettingsConfigDict(env_prefix="redis_")

    host: str = "redis"
    port: PositiveInt = 6379
    queue: str = "minhash"


class NotificationConfig(BaseSettings):
    """Configure how to send notifications."""

    sender: str = "do-not-reply@bonsai.app"
    sender_name: str = "Bonsai"


class BasePeriodicTaskConfig(BaseSettings):
    """Generic configuration for periodic integrity check task."""

    enabled: bool = True  # enable/disable background task processing
    cron: str = "0 12 * * SAT"  # cron schedule for periodic tasks
    queue: str = "minhash"  # redis queue name for periodic tasks


class PeriodicIntegrityCheckConfig(BasePeriodicTaskConfig):
    """Configure scheudling of background tasks."""

    model_config = SettingsConfigDict(env_prefix="integrity_task_")

    cron: str = "0 12 * * SAT"  # cron schedule for periodic tasks


class CleanupRemovedFilesConfig(BasePeriodicTaskConfig):
    """Configure scheudling of background tasks."""

    model_config = SettingsConfigDict(env_prefix="purge_files_task_")

    cron: str = "0 * * * *"  # cron schedule for periodic tasks


class Notification(BaseSettings):
    """Setup notification service."""

    api_url: HttpUrl | None = None
    recipient: list[str] = []
    integrity_report_level: IntegrityReportLevel = IntegrityReportLevel.NEVER


class Settings(BaseSettings):
    """Minhash service settings."""

    kmer_size: PositiveInt = 31
    signature_dir: Path = Path("/data/signature_db")
    index_format: IndexFormat = IndexFormat.SBT
    trash_dir: DirectoryPath = Field(
        default_factory=_get_trash_dir, description="Directory for trashed files"
    )

    redis: RedisConfig = RedisConfig()
    mongodb: MongodbConfig = MongodbConfig()
    # periodic tasks
    periodic_integrity_check: PeriodicIntegrityCheckConfig = (
        PeriodicIntegrityCheckConfig()
    )
    cleanup_removed_files: CleanupRemovedFilesConfig = CleanupRemovedFilesConfig()

    # setup notification settings
    notification: Notification = Notification()

    log_level: LogLevel = LogLevel.INFO

    @field_validator("trash_dir", mode="before")
    @classmethod
    def ensure_trash_dir_exists(cls, val: Path) -> Path:
        """Ensure that the trash directory exists."""
        val.mkdir(parents=True, exist_ok=True)
        return val

    @model_validator(mode="after")
    def validate_report_service_config(self):
        """Ensure that API url is set when errors should be reported."""
        requires_notifier = self.notification.integrity_report_level in {
            IntegrityReportLevel.ERROR,
            IntegrityReportLevel.WARNING,
        }
        if requires_notifier and not self.is_notification_configured:
            raise ValidationError("Notification serivce URL must be configures.")
        return self

    @computed_field
    @property
    def is_notification_configured(self) -> bool:
        """Return true URL to notificaiton API has been configured."""
        return self.notification.api_url is not None

    def build_logging_config(self) -> dict[str, Any]:
        """Build logging configuration dictionary."""
        log_config = deepcopy(LOG_CONFIG)
        # update log levels
        log_config["handlers"]["default"]["level"] = self.log_level.value
        log_config["loggers"]["root"]["level"] = self.log_level.value
        return log_config


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


def configure_logging(settings: Settings) -> None:
    """Configure logging from settings."""
    logging_config.dictConfig(settings.build_logging_config())


cnf = Settings()
