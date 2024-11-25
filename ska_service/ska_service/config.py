"""Configuration for minhash service"""

from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(StrEnum):
    """Valid log levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Settings(BaseSettings):
    """SKA typing configuration."""

    index_dir: str = "/data/index_files"
    # redis variables
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_queue: str = "ska"
    # logging
    log_level: LogLevel = LogLevel.INFO

    model_config = SettingsConfigDict(use_enum_values=True)


settings = Settings()
