"""Utility functions for various cli commands."""

import asyncio
import logging

import click
from email_validator import EmailNotValidError
from pydantic import validate_email

LOG = logging.getLogger(__name__)


class EmailType(click.ParamType):
    name = "email"

    def convert(self, value: str, param: click.Option, ctx: click.Context):
        """Validate emails using email validator module."""
        try:
            validate_email(value)
            return value
        except EmailNotValidError:
            self.fail(f"{value} is not a valid email", param, ctx)


def run_async(coro):
    """Run async coroutine with exception logging."""
    try:
        return asyncio.run(coro)
    except Exception as exc:
        LOG.exception("Async task failed", exc_info=exc)
        raise
