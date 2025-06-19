"""Describes sample, variant or analysis quality."""

from pydantic import BaseModel

from ..base import ApiModel
from ..constants import (BadSampleQualityAction, ResistanceLevel,
                         SampleQcStatus, TagSeverity)


class VariantRejectionReason(BaseModel):
    """Data model for reasons rejecting a variant."""

    label: str
    description: str
    label_class: TagSeverity = TagSeverity.INFO


VARIANT_REJECTION_REASONS = [
    VariantRejectionReason(label="LOW", description="Low coverage"),
    VariantRejectionReason(label="A", description="Likely artifact"),
    VariantRejectionReason(label="SYN", description="Synonymous mutation"),
]


class SampleQcClassification(ApiModel):  # pylint: disable=too-few-public-methods
    """The classification of sample quality."""

    status: SampleQcStatus = SampleQcStatus.UNPROCESSED
    action: BadSampleQualityAction | None = None
    comment: str = ""


class VariantQcAnnotation(ApiModel):  # pylint: disable=too-few-public-methods
    """User variant annotation."""

    variant_ids: list[str]
    verified: SampleQcClassification | None = None
    reason: VariantRejectionReason | None = None
    phenotypes: list[str] | None = None
    resistance_lvl: ResistanceLevel | None = None
