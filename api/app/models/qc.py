"""QC data models."""
from enum import Enum
from typing import List

from .base import RWModel
from .antibiotics import AntibioticInfo


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


class VariantAnnotation(RWModel):  # pylint: disable=too-few-public-methods
    """User variant annotation."""

    variant_ids: List[str]
    verified: SampleQcClassification = SampleQcClassification.UNPROCESSED
    reason: str | None = None
    phenotypes: List[str] | None = None
