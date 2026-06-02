from enum import StrEnum


class RouterTags(StrEnum):
    """Tag names for API routes."""

    ANALYSIS = "analysis"
    AUTH = "auth"
    CLUSTER = "cluster"
    EXPORT = "export"
    GENOMIC_RESOURCE = "genomic-resource"
    GROUP = "groups"
    JOB = "jobs"
    LOCATION = "location"
    MEM = "memberships"
    META = "metadata"
    MINHASH = "minhash"
    PIPELINE_RUNS = "pipeline_runs"
    REFERENCE_GENOME = "reference_genome"
    REFERENCE = "reference"
    SAMPLE = "sample"
    USR = "user"
    FILES = "files"
    QUALITY = "quality"
    SEARCH = "search"