"""Functions for handling redis jobs."""

from enum import StrEnum

from bonsai_api.models.base import RWModel


class SubmittedJob(RWModel):  # pylint: disable=too-few-public-methods
    """Container for submitted jobs."""

    id: str
    task: str

