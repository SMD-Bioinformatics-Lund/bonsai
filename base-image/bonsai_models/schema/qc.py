"""Describes sample, variant or analysis quality."""

from pydantic import BaseModel

from ..base import RWModel
from ..constants import (BadSampleQualityAction, ResistanceLevel,
                         SampleQcStatus, TagSeverity)


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


class SampleQcClassification(RWModel):  # pylint: disable=too-few-public-methods
    """The classification of sample quality."""

    status: SampleQcStatus = SampleQcStatus.UNPROCESSED
    action: BadSampleQualityAction | None = None
    comment: str = ""


class VariantQcAnnotation(RWModel):  # pylint: disable=too-few-public-methods
    """User variant annotation."""

    variant_ids: list[str]
    verified: SampleQcClassification | None = None
    reason: VaraintRejectionReason | None = None
    phenotypes: list[str] | None = None
    resistance_lvl: ResistanceLevel | None = None
