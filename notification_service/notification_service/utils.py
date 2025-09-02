"""Utility functions."""

from logging import config as logging_config
from pathlib import Path
from importlib import resources

from .config import Settings


def configure_logging(cnf: Settings) -> None:
    """Configure logging from settings."""
    logging_config.dictConfig(cnf.build_logging_config())
