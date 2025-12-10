"""Models related to sample memberships."""

from typing import TypeAlias

from pydantic import BaseModel, Field

from .base import RWModel


class MembershipEdge(BaseModel):
    """Describe a relationship between a sample and group."""

    sample_id: str
    group_id: str


MembershipEdges: TypeAlias = list[MembershipEdge]


class SampleMembershipInput(RWModel):  # pylint: disable=too-few-public-methods
    """Input model for sample group membership."""

    sample_ids: list[str] = Field(..., description="Sample ids")
    group_ids: list[str] = Field(..., description="Group ids")
