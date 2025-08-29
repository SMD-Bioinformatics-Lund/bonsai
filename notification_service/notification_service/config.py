"""Application settings."""

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import ConfigDict, Field, PositiveInt, computed_field
from pydantic_settings import BaseSettings


class LogLevel(StrEnum):
    """Log level options."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class RedisConfig(BaseSettings):
    """Redis configuration."""

    model_config = ConfigDict(env_prefix="redis_")

    host: str = "redis"
    port: PositiveInt = 6379
    queue: str = "notification"


class SmtpConfig(BaseSettings):
    """SMTP server configuration."""

    model_config = ConfigDict(env_prefix="smtp_")

    host: str | None = None
    port: int = 25
    timeout: int = Field(default=60, description="Conection timeout in seconds.")
    use_tls: bool = False
    use_ssl: bool = False


class Settings(BaseSettings):
    """Email service settings."""

    redis: RedisConfig = RedisConfig()
    smtp: SmtpConfig = SmtpConfig()

    sender_email: str = "noreply@example.com"
    sender_name: str = "Notification"

    template_dir: Path = Path("templates/")

    log_level: LogLevel = LogLevel.INFO

    @computed_field
    @property
    def use_redis(self) -> bool:
        """Use redis queue if configuration is valid."""
        return isinstance(self.smtp.host, str)

    def build_logging_config(self) -> dict[str, Any]:
        """Build logging configuration dictionary."""
        log_config = LOG_CONFIG.copy()
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


settings = Settings()
