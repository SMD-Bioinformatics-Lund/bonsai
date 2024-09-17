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
    display_name: str = Field(..., min_length=1, max_length=45)
    description: str | None = None


class OverviewTableColumn(BaseModel):  # pylint: disable=too-few-public-methods
    """Definition of how to display and function of overview table."""

    id: str = Field(..., description="Column id")
    label: str = Field(..., description="Display name")
    path: str = Field(..., description="JSONpath describing how to access the data")
    # display params
    hidden: bool = False
    type: str = Field("string", description="Data type")
    sortable: bool = False
    filterable: bool = False
    filter_type: str | None = None
    filter_param: str | None = None


VALID_COLUMNS = [
    OverviewTableColumn(
        id="sample_btn",
        label="Open sample",
        type="sample_btn",
        path="$.sample_id",
    ),
    OverviewTableColumn(
        id="sample_id",
        label="Sample Id",
        path="$.sample_id",
        hidden=True,
        sortable=True,
    ),
    OverviewTableColumn(
        id="sample_name",
        label="Name",
        path="$.sample_name",
        sortable=True,
    ),
    OverviewTableColumn(
        id="lims_id",
        label="LIMS id",
        path="$.lims_id",
        sortable=True,
    ),
    OverviewTableColumn(
        id="sequencing_run",
        label="Sequencing run",
        path="$.sequencing_run",
        sortable=True,
    ),
    OverviewTableColumn(
        id="tags",
        label="Tags",
        type="tags",
        path="$.tags",
    ),
    OverviewTableColumn(
        id="taxonomic_name",
        label="Major species",
        type="taxonomic_name",
        path="$.species_prediction.scientific_name",
        sortable=True,
    ),
    OverviewTableColumn(
        id="qc",
        label="QC",
        path="$.qc_status.status",
        sortable=True,
    ),
    OverviewTableColumn(
        id="mlst",
        label="MLST ST",
        path="$.mlst.sequence_type",
        sortable=True,
        filterable=True,
    ),
    OverviewTableColumn(
        id="stx",
        label="STX typing",
        path="$.stx",
        sortable=True,
        filterable=True,
    ),
    OverviewTableColumn(
        id="oh",
        label="OH typing",
        path="$.oh_type",
        sortable=True,
        filterable=True,
    ),
    OverviewTableColumn(
        id="profile",
        label="Analysis profile",
        path="$.profile",
        sortable=True,
        filterable=True,
    ),
    OverviewTableColumn(
        id="cdate",
        label="Date",
        type="date",
        path="$.created_at",
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
