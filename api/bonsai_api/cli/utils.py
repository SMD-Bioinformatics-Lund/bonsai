"""Utility functions for various cli commands."""

import logging
from csv import DictWriter
from io import StringIO, TextIOWrapper

import click
from bonsai_api.db.verify import MissingFile
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


def create_missing_file_report(
    missing_files: list[MissingFile], file: StringIO | TextIOWrapper
) -> StringIO | TextIOWrapper:
    """Create csv report of missing files."""
    n_samples = len({row.sample_id for row in missing_files})
    print(
        f"Found {n_samples} with a total of {len(missing_files)} missing files.\n",
        file=file,
    )
    writer = DictWriter(file, fieldnames=list(MissingFile.model_fields))
    writer.writeheader()
    for missing_file in missing_files:
        writer.writerow(missing_file.model_dump())
    return file
