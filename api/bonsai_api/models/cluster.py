"""Clustering information"""
from enum import Enum


class DistanceMethod(Enum):  # pylint: disable=too-few-public-methods
    """Valid distance methods for hierarchical clustering of samples."""

    JACCARD = "jaccard"
    HAMMING = "hamming"


class ClusterMethod(Enum):  # pylint: disable=too-few-public-methods
    """Index of methods for hierarchical clustering of samples."""

    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"
    NJ = "neighbor_joining"


class TypingMethod(str, Enum):  # pylint: disable=too-few-public-methods
    """Supported typing methods."""

    MLST = "mlst"
    CGMLST = "cgmlst"
    SKA = "ska"
    MINHASH = "minhash"
