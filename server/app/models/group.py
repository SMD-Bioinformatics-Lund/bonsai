"""Routes related to collections of samples."""
from pydantic import BaseModel, Field, FileUrl
from typing import List, Dict
from .base import DBModelMixin, RWModel, PyObjectId


class Image(BaseModel):
    url: FileUrl
    name: str


FilterParams = List[
    Dict[str, str | int | float],
]


class IncludedSamples(RWModel):
    """Object for keeping track of included samples in a group"""

    included_samples: List[PyObjectId] = Field(..., alias="includedSamples")


class UpdateIncludedSamples(IncludedSamples):
    """Object for keeping track of included samples in a group"""

    pass


class GroupBase(IncludedSamples):
    """Basic specie information."""

    group_id: str = Field(..., alias="groupId")
    display_name: str = Field(..., alias="displayName")
    image: Image | None = Field(None)


class OverviewTableColumn(BaseModel):
    """Definition of how to display and function of overview table."""

    hidden: bool = Field(False)
    type: str
    name: str
    label: str
    sortable: bool = Field(False)
    filterable: bool = Field(False)
    filter_type: str | None = Field(None, alias="filterType")
    filter_param: str | None = Field(None, alias="filterParam")


class GroupInCreate(GroupBase):
    table_columns: List[OverviewTableColumn] = Field(..., alias="tableColumns")


class GroupInfoDatabase(DBModelMixin, GroupInCreate):
    pass


class GroupInfoOut(GroupBase):
    pass
