"""Routes related to collections of samples."""
from typing import Dict, List

from pydantic import BaseModel, Field, FileUrl

from .base import DBModelMixin, ModifiedAtRWModel, ObjectId, PyObjectId
from .sample import SampleInDatabase


class Image(BaseModel):
    url: FileUrl
    name: str


FilterParams = List[
    Dict[str, str | int | float],
]


class IncludedSamples(ModifiedAtRWModel):
    """Object for keeping track of included samples in a group"""

    included_samples: List[PyObjectId | SampleInDatabase] = Field(..., alias="includedSamples")

    class Config:
        json_encoders = {ObjectId: str}


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
