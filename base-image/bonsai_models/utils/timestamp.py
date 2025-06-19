"""
This module provides utility functions for working with timestamps.

Functions:
    get_timestamp() -> datetime.datetime:
        Returns the current UTC datetime as a timezone-aware datetime object.
"""
import datetime


def get_timestamp() -> datetime.datetime:
    """Returns the current UTC datetime as a timezone-aware datetime object."""
    return datetime.datetime.now(tz=datetime.UTC)
