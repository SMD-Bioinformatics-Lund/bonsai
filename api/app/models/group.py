"""Routes related to collections of samples."""
from typing import Dict, List

from prp.models.phenotype import ElementType
from pydantic import BaseModel, Field

from .base import DBModelMixin, ModifiedAtRWModel, ObjectId
from .sample import SampleSummary

FilterParams = List[Dict[str, str | int | float],]


class IncludedSamples(ModifiedAtRWModel):  # pylint: disable=too-few-public-methods
    """Object for keeping track of included samples in a group"""

    included_samples: List[str | SampleSummary]

    class Config:  # pylint: disable=too-few-public-methods
        """Make mongodb object id serializable."""

        json_encoders = {ObjectId: str}


class UpdateIncludedSamples(IncludedSamples):  # pylint: disable=too-few-public-methods
    """Object for keeping track of included samples in a group"""


class GroupBase(IncludedSamples):  # pylint: disable=too-few-public-methods
    """Basic specie information."""

    group_id: str = Field(..., min_length=5)
    display_name: str = Field(..., min_length=1)


class OverviewTableColumn(BaseModel):  # pylint: disable=too-few-public-methods
    """Definition of how to display and function of overview table."""

    hidden: bool = Field(False)
    type: str
    path: str
    label: str
    sortable: bool = Field(False)
    filterable: bool = Field(False)
    filter_type: str | None = Field(None)
    filter_param: str | None = Field(None)


class GroupInCreate(GroupBase):  # pylint: disable=too-few-public-methods
    """Defines expected input format for groups."""

    table_columns: List[OverviewTableColumn] = Field(...)
    validated_genes: Dict[ElementType, List[str]] | None = Field({})


class GroupInfoDatabase(
    DBModelMixin, GroupInCreate
):  # pylint: disable=too-few-public-methods
    """Defines group info stored in the databas."""


class GroupInfoOut(GroupBase):  # pylint: disable=too-few-public-methods
    """Defines output structure of group info."""
