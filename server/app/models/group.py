"""Routes related to collections of samples."""
from typing import Dict, List

from pydantic import BaseModel, Field

from .base import DBModelMixin, ModifiedAtRWModel, ObjectId, PyObjectId
from .phenotype import ElementType
from .sample import SampleSummary

FilterParams = List[Dict[str, str | int | float],]


class IncludedSamples(ModifiedAtRWModel):
    """Object for keeping track of included samples in a group"""

    included_samples: List[str | SampleSummary]

    class Config:
        json_encoders = {ObjectId: str}


class UpdateIncludedSamples(IncludedSamples):
    """Object for keeping track of included samples in a group"""

    pass


class GroupBase(IncludedSamples):
    """Basic specie information."""

    group_id: str = Field(..., min_length=5)
    display_name: str


class OverviewTableColumn(BaseModel):
    """Definition of how to display and function of overview table."""

    hidden: bool = Field(False)
    type: str
    path: str
    label: str
    sortable: bool = Field(False)
    filterable: bool = Field(False)
    filter_type: str | None = Field(None)
    filter_param: str | None = Field(None)


class GroupInCreate(GroupBase):
    table_columns: List[OverviewTableColumn] = Field(...)
    validated_genes: Dict[ElementType, List[str]] | None = Field({})


class GroupInfoDatabase(DBModelMixin, GroupInCreate):
    pass


class GroupInfoOut(GroupBase):
    pass
