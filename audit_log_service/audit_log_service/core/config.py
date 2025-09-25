"""Application settings."""

from enum import StrEnum
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(StrEnum):
    """Log level options."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class MongodbConfig(BaseSettings):
    """MongoDB configuration for minhash service."""

    model_config = SettingsConfigDict(env_prefix="mongodb_")

    uri: str = Field(
        default="mongodb://mongodb:27017/", description="MongoDb connection URI."
    )
    database: str = Field(default="bonsai", description="The database where logs are stored.")
    collection: str = Field(default="events", description="The collection for storing events.")


class Settings(BaseSettings):
    """Base app settings."""

    service_name: str = "audit-log-service"
    log_level: LogLevel = LogLevel.INFO
    log_format: Literal["json", "text"] = "json"
    mongo: MongodbConfig = MongodbConfig()

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


def get_settings() -> Settings:
    """Get a settings instance."""
    return Settings()
