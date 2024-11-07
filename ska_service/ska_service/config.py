"""Configuration for minhash service"""

import logging
from enum import StrEnum

from pydantic_settings import BaseSettings


class LogLevel(StrEnum):
    """Valid log levels."""

    DEBUGGER = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR


class Settings(BaseSettings):
    """SKA typing configuration."""

    index_dir: str = "/data/index_files"
    # redis variables
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_queue: str = "minhash"
    # logging
    log_level: LogLevel = LogLevel.WARNING


settings = Settings()
