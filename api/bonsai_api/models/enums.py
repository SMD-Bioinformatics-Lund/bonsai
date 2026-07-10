
from enum import StrEnum


class Visibility(StrEnum):
    """Determines the visibilty of a record."""

    PRIVATE = "private"
    ORG = "organization"
    PUBLIC = "public"


class SequencingPlatforms(StrEnum):
    """Supported sequencing platforms."""

    ILLUMUNA = "illumina"
    IONTORRENT = "ion torrent"
    ONT = "oxford nanopore technologies"
    BGI = "bgi"
    PACBIO = "Pacific Biosciences"


class ExportStatus(StrEnum):
    """Status for LIMS export operations."""

    NOT_EXPORTED = "not_exported"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class TypingMethod(StrEnum):  # pylint: disable=too-few-public-methods
    """Supported typing methods."""

    MLST = "mlst"
    CGMLST = "cgmlst"
    SKA = "ska"
    MINHASH = "minhash"


class ClusterStrategy(StrEnum):
    """Supported clustering strategies."""

    # SDK hierarchical clustering
    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"
    WEIGHTED = "weighted"
    CENTROID = "centroid"

    # SDK MST
    MST = "mst"

    # GrapeTree
    MSTREE_V1 = "MSTree"
    MSTREE_V2 = "MSTreeV2"
    NJ = "NJ"
    RAPID_NJ = "RapidNJ"
    NINJA = "ninja"


class ClusterMethod(StrEnum):  # pylint: disable=too-few-public-methods
    """Index of methods for hierarchical clustering of samples."""

    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"
    NJ = "neighbor_joining"


class FileSources(StrEnum):
    """Valid file sources."""

    REFERENCE_GENOMES = "reference-genomes"
    GENOMIC_RESOURCES = "genomic-resources"
