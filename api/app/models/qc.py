"""QC data models."""
from enum import Enum

from pydantic import BaseModel, Field

from .base import RWModel


class SampleQcClassification(Enum):
    """QC statuses."""

    # phenotype
    PASSED = "passed"
    FAILED = "failed"
    UNPROCESSED = "unprocessed"


class BadSampleQualityAction(Enum):
    """Actions that could be taken if a sample have low quality."""

    # phenotype
    REEXTRACTION = "new extraction"
    RESEQUENCE = "resequence"
    FAILED = "permanent fail"


class QcClassification(RWModel):  # pylint: disable=too-few-public-methods
    """The classification of sample quality."""

    status: SampleQcClassification = SampleQcClassification.UNPROCESSED
    action: BadSampleQualityAction | None = None
    comment: str = ""


class QcSoftware(Enum):
    """Valid tools."""

    QUAST = "quast"
    FASTQC = "fastqc"
    POSTALIGNQC = "postalignqc"


class QuastQcResult(BaseModel):  # pylint: disable=too-few-public-methods
    """Assembly QC metrics."""

    total_length: int
    reference_length: int
    largest_contig: int
    n_contigs: int
    n50: int
    assembly_gc: float
    reference_gc: float
    duplication_ratio: float


class PostAlingQcResult(BaseModel):  # pylint: disable=too-few-public-methods
    """PostAlignQc workflow results."""

    ins_size: int = Field(..., description="Average insert size")
    ins_size_dev: int = Field(..., description="Insert size standard deviation")
    mean_cov: int = Field(..., description="Average read coverage")
    pct_above_x: dict[str, float] = Field(..., description="Read coverage distribution")
    mapped_reads: int = Field(..., description="Number of mapped reads")
    tot_reads: int
    iqr_median: float
    dup_pct: float = Field(..., description="Percentage of duplicated reads")
    dup_reads: int = Field(..., description="Number of duplicated reads")


class QcMethodIndex(RWModel):  # pylint: disable=too-few-public-methods
    """QC results container.  Based on Mongo db Attribute pattern.

    Reference: https://www.mongodb.com/developer/products/mongodb/attribute-pattern/
    """

    software: QcSoftware
    version: str | None
    result: QuastQcResult | PostAlingQcResult
