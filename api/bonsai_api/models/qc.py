"""QC data models."""

from enum import StrEnum

from pydantic import BaseModel

from .base import RWModel
from .tags import TagSeverity


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


class QcClassification(RWModel):  # pylint: disable=too-few-public-methods
    """The classification of sample quality."""

    status: SampleQcClassification = SampleQcClassification.UNPROCESSED
    action: BadSampleQualityAction | None = None
    comment: str = ""
