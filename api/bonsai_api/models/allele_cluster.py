"""Sample accounting for allele-based clustering."""

from .base import RWModel


class UnplacedSample(RWModel):
    """A selected sample without enough information to place in an allele tree."""

    sample_id: str
    label: str
    reason: str = "No usable allele calls are available."
