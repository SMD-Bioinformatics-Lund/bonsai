"""Compatibility of selected typing schemes for allele clustering."""

from pydantic import Field

from bonsai_api.models.base import RWModel


class AlleleSchemeNoticeGroup(RWModel):
    """A displayed notice category and every sample it contains."""

    detail: str
    sample_ids: list[str]


class AlleleSchemeValidation(RWModel):
    """Whether scheme identity and the full locus definitions are compatible."""

    can_cluster: bool
    notice: str | None = None
    details: list[str] = Field(default_factory=list)
    notice_groups: list[AlleleSchemeNoticeGroup] = Field(default_factory=list)
