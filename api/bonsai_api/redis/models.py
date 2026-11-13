"""Functions for handling redis jobs."""

from enum import Enum
from typing import TypedDict

from ..models.base import RWModel


class SkaIndexInput(TypedDict):
    """Sample identifiers and SKA index passed to the clustering worker."""

    sample_id: str
    external_sample_id: str
    ska_index: str


class SubmittedJob(RWModel):  # pylint: disable=too-few-public-methods
    """Container for submitted jobs."""

    id: str
    task: str


class ClusterMethod(Enum):  # pylint: disable=too-few-public-methods
    """Index of methods for hierarchical clustering of samples."""

    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"


class MsTreeMethods(Enum):  # pylint: disable=too-few-public-methods
    """Valid cluter methods."""

    MSTREE_V1 = "MSTree"
    MSTREE_V2 = "MSTreeV2"
    NEIGHBOR_JOINING = "NJ"
    RAPID_NJ = "RapidNJ"
    NINJA = "ninja"
