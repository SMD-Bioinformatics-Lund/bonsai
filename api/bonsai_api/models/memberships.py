"""Models related to sample memberships."""


from typing import TypeAlias

from pydantic import BaseModel, Field

from .base import RWModel


MembershipsQueryResponse: TypeAlias = dict[str, list[str]]


class SampleGroupLink(BaseModel):
    """Keep track of a sample-group relationship."""

    sample_id: str
    group_ids: list[str]


class GroupSampleLink(BaseModel):
    """Keep track of a sample-group relationship."""

    group_id: str
    sample_ids: list[str]


class SampleMembershipInput(RWModel):  # pylint: disable=too-few-public-methods
    """Input model for sample group membership."""

    sample_ids: list[str] = Field(..., description="Sample ids")
    group_ids: list[str] = Field(..., description="Group ids")
