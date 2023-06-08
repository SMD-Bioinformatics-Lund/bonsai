"""QC data models."""
from enum import Enum

from pydantic import BaseModel, Field

from .base import RWModel


class QcSoftware(Enum):
    """Valid tools."""

    QUAST = "quast"
    FASTQC = "fastqc"
    POSTALIGNQC = "postalignqc"


class QuastQcResult(BaseModel):
    """Assembly QC metrics."""

    total_length: int
    reference_length: int
    largest_contig: int
    n_contigs: int
    n50: int
    assembly_gc: float
    reference_gc: float
    duplication_ratio: float


class PostAlingQcResult(BaseModel):
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


class QcMethodIndex(RWModel):
    software: QcSoftware
    version: str | None
    result: QuastQcResult | PostAlingQcResult
