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

    hidden: bool = False
    type: str = Field(..., description="Data type")
    path: str = Field(..., description="JSONpath describing how to access the data")
    label: str = Field(..., description="Display name")
    sortable: bool = False
    filterable: bool = False
    filter_type: str | None = None
    filter_param: str | None = None


VALID_COLUMNS = [
    OverviewTableColumn(
        label="Sample Id",
        type="sampleid",
        path='$.sample_id',
        sortable=True,
    ),
    OverviewTableColumn(
        label="Tags",
        type="tags",
        path='$.tags',
    ),
    OverviewTableColumn(
        label="Major species",
        type="taxonomic_name",
        path='$.species_prediction.scientific_name',
        sortable=True,
    ),
    OverviewTableColumn(
        label="QC",
        type="qc",
        path='$.qc_status.status',
        sortable=True,
    ),
    OverviewTableColumn(
        label="MLST ST",
        type="text",
        path='$.created_at',
        sortable=True,
        filterable=True,
    ),
    OverviewTableColumn(
        label="Analysis profile",
        type="text",
        path='$.profile',
        sortable=True,
        filterable=True,
    ),
    OverviewTableColumn(
        label="Date",
        type="date",
        path='$.created_at',
        sortable=True,
    ),
]


class GroupInCreate(GroupBase):  # pylint: disable=too-few-public-methods
    """Defines expected input format for groups."""

    table_columns: List[OverviewTableColumn] = Field(description="Columns to display")
    validated_genes: Dict[ElementType, List[str]] | None = Field({})


class GroupInfoDatabase(
    DBModelMixin, GroupInCreate
):  # pylint: disable=too-few-public-methods
    """Defines group info stored in the databas."""


class GroupInfoOut(GroupBase):  # pylint: disable=too-few-public-methods
    """Defines output structure of group info."""
