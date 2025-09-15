"""For configuring logging"""

from logging import config as logging_config
from typing import Any

from .config import Settings

def configure_logging(settings: Settings):
    """Setup logging"""
    log_config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
        },
        "handlers": {
            "default": {
                "level": settings.log_level.value,
                "formatter": "standard",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",  # Default is stderr
            },
        },
        "loggers": {
            "root": {  # root logger
                "handlers": ["default"],
                "level": settings.log_level.value,
                "propagate": False,
            },
        },
    }
    logging_config.dictConfig(log_config)