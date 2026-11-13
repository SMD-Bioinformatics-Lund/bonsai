"""Compatibility of selected typing schemes for allele clustering."""

from bonsai_api.models.base import RWModel


class AlleleSchemeValidation(RWModel):
    """Whether scheme identity and the full locus definitions are compatible."""

    can_cluster: bool
    notice: str | None = None
