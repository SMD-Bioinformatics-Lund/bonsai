"""QC data models."""

from enum import StrEnum

from pydantic import BaseModel, Field

from .base import RWModel
from .tags import TagSeverity
from .constants import QcSoftware


class ValidQualityStr(StrEnum):
    """Valid strings for qc entries."""

    LOWCONTIGQUAL = "-"


class QuastQcResult(BaseModel):
    """Assembly QC metrics."""

    total_length: int
    reference_length: int | None = None
    largest_contig: int
    n_contigs: int
    n50: int
    ng50: int | ValidQualityStr | None = None
    assembly_gc: float
    reference_gc: float | None = None
    duplication_ratio: float | None = None


class PostAlignQcResult(BaseModel):
    """Alignment QC metrics."""

    ins_size: int | None = None
    ins_size_dev: int | None = None
    mean_cov: int
    pct_above_x: dict[str, float]
    n_reads: int
    n_mapped_reads: int
    n_read_pairs: int
    coverage_uniformity: float | None = None
    quartile1: float
    median_cov: float
    quartile3: float


class GenomeCompleteness(BaseModel):
    """cgMLST QC metric."""

    n_missing: int = Field(..., description="Number of missing cgMLST alleles")


class GambitcoreQcResult(BaseModel):
    """Gambitcore genome completeness QC metrics."""

    scientific_name: str | None = None
    completeness: float | None = None
    assembly_core: str | None = None
    closest_accession: str | None = None
    closest_distance: float | None = None
    assembly_kmers: int | None = None
    species_kmers_mean: int | None = None
    species_kmers_std_dev: int | None = None
    assembly_qc: str


class QcMethodIndex(RWModel):
    """QC results container.

    Based on Mongo db Attribute pattern.
    Reference: https://www.mongodb.com/developer/products/mongodb/attribute-pattern/
    """

    software: QcSoftware
    version: str | None = None
    result: QuastQcResult | PostAlignQcResult | GenomeCompleteness | GambitcoreQcResult


class VaraintRejectionReason(BaseModel):
    """Data model for reasons rejecting a variant."""

    label: str
    description: str
    label_class: TagSeverity = TagSeverity.INFO


VARIANT_REJECTION_REASONS = [
    VaraintRejectionReason(label="LOW", description="Low coverage"),
    VaraintRejectionReason(label="A", description="Likely artifact"),
    VaraintRejectionReason(label="SYN", description="Synonymous mutation"),
]


class SampleQcClassification(StrEnum):
    """QC statuses."""

    # phenotype
    PASSED = "passed"
    FAILED = "failed"
    UNPROCESSED = "unprocessed"


class BadSampleQualityAction(StrEnum):
    """Actions that could be taken if a sample have low quality."""

    # phenotype
    REEXTRACTION = "new extraction"
    RESEQUENCE = "resequence"
    FAILED = "permanent fail"


class ResistanceLevel(StrEnum):
    """The level of resistance a gene or variant yeilds."""

    HIGH = "high"
    LOW = "low"


class QcClassification(RWModel):  # pylint: disable=too-few-public-methods
    """The classification of sample quality."""

    status: SampleQcClassification = SampleQcClassification.UNPROCESSED
    action: BadSampleQualityAction | None = None
    comment: str = ""


class VariantAnnotation(RWModel):  # pylint: disable=too-few-public-methods
    """User variant annotation."""

    variant_ids: list[str]
    verified: SampleQcClassification | None = None
    reason: VaraintRejectionReason | None = None
    phenotypes: list[str] | None = None
    resistance_lvl: ResistanceLevel | None = None
