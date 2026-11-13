"""Validation and accounting for allele-based clustering."""

from pydantic import Field

from .base import RWModel


class UnplacedSample(RWModel):
    """A selected sample without enough information to place in an allele tree."""

    sample_id: str
    label: str
    reason: str = "No usable allele calls are available."


class AlleleClusterValidation(RWModel):
    """Whether the selected samples can be compared using one typing method."""

    can_cluster: bool
    notice: str | None = None
    unplaced_samples: list[UnplacedSample] = Field(default_factory=list)
