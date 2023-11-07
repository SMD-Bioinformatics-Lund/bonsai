"""Clustering information"""
from enum import Enum


class DistanceMethod(Enum):
    """Index of methods for calculating the distance matrix during hierarchical clustering of samples."""

    JACCARD = "jaccard"
    HAMMING = "hamming"


class ClusterMethod(Enum):
    """Index of methods for hierarchical clustering of samples."""

    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"
    NJ = "neighbor_joining"


class TypingMethod(str, Enum):
    MLST = "mlst"
    CGMLST = "cgmlst"
    MINHASH = "minhash"
