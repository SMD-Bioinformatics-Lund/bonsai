from enum import StrEnum


class RouterTags(StrEnum):
    """Tag names for API routes."""

    ANALYSIS = "analysis"
    AUTH = "auth"
    CLUSTER = "cluster"
    EXPORT = "export"
    GENOMIC_ASSET = "genomic-assets"
    GROUP = "groups"
    JOB = "jobs"
    LOCATION = "location"
    MEM = "memberships"
    META = "metadata"
    MINHASH = "minhash"
    PIPELINE_RUNS = "pipeline_runs"
    REFERENCE_GENOME = "reference_genome"
    RESOURCE = "resource"
    SAMPLE = "sample"
    USR = "user"
