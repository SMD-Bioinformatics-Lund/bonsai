"""Module for setting up the redis queue and scheduling jobs."""

from enum import Enum

from ..models.base import RWModel
from ..models.cluster import TypingMethod, DistanceMethod
from .queue import redis


class SubmittedJob(RWModel):
    """Container for submitted jobs."""

    id: str
    task: str


class ClusterMethod(Enum):
    """Index of methods for hierarchical clustering of samples."""

    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"


class MsTreeMethods(Enum):
    """Valid cluter methods."""

    MSTREE_V1 = "MSTree"
    MSTREE_V2 = "MSTreeV2"
    NEIGHBOR_JOINING = "NJ"
    RAPID_NJ = "RapidNJ"
    NINJA = "ninja"