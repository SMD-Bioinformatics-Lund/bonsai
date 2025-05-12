"""Clustering information"""

from enum import StrEnum


class DistanceMethod(StrEnum):  # pylint: disable=too-few-public-methods
    """Valid distance methods for hierarchical clustering of samples."""

    JACCARD = "jaccard"
    HAMMING = "hamming"


class ClusterMethod(StrEnum):  # pylint: disable=too-few-public-methods
    """Index of methods for hierarchical clustering of samples."""

    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"
    NJ = "neighbor_joining"


class TypingMethod(StrEnum):  # pylint: disable=too-few-public-methods
    """Supported typing methods."""

    MLST = "mlst"
    CGMLST = "cgmlst"
    SKA = "ska"
    MINHASH = "minhash"
