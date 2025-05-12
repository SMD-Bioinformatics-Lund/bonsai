"""Routes related to collections of samples."""

from typing import Dict, List

from prp.models.phenotype import ElementType
from pydantic import BaseModel, ConfigDict, Field

from .base import DBModelMixin, ModifiedAtRWModel, ObjectId, RWModel
from .sample import SampleSummary

FilterParams = List[Dict[str, str | int | float],]


class IncludedSamples(RWModel):  # pylint: disable=too-few-public-methods
    """Object for keeping track of included samples in a group"""

    included_samples: List[str | SampleSummary] = []

    model_config = ConfigDict(json_encoders={ObjectId: str})


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
    type: str = Field(default="string", description="Data type")
    sortable: bool = False
    filterable: bool = False
    filter_type: str | None = None
    filter_param: str | None = None


VALID_BASE_COLS: list[OverviewTableColumn] = [
    OverviewTableColumn(
        id="sample_btn",
        label="",
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
]

# Prediction result columns
VALID_PREDICTION_COLS: list[OverviewTableColumn] = [
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
        id="assay",
        label="Assay",
        path="$.assay",
        sortable=True,
    ),
    OverviewTableColumn(
        id="release_life_cycle",
        label="Release life cycle",
        path="$.release_life_cycle",
        sortable=True,
    ),
    OverviewTableColumn(
        id="sequencing_run",
        label="Sequencing run",
        path="$.sequencing_run",
        sortable=True,
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
        type="qc",
        path="$.qc_status.status",
        sortable=True,
    ),
    OverviewTableColumn(
        id="profile",
        label="Analysis profile",
        path="$.profile",
        type="list",
        sortable=True,
        filterable=True,
    ),
    OverviewTableColumn(
        id="comments",
        label="Comments",
        type="comments",
        path="$.comments",
    ),
    OverviewTableColumn(
        id="tags",
        label="Tags",
        type="tags",
        path="$.tags",
    ),
    OverviewTableColumn(
        id="mlst",
        label="MLST ST",
        path="$.mlst",
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
        id="cdate",
        label="Date",
        type="date",
        path="$.created_at",
        sortable=True,
    ),
]

# Prediction result columns
VALID_QC_COLS = [
    OverviewTableColumn(
        id="sample_name",
        label="Name",
        path="$.sample_name",
        sortable=True,
    ),
    OverviewTableColumn(
        id="sequencing_run",
        label="Sequencing run",
        path="$.sequencing_run",
        sortable=True,
    ),
    OverviewTableColumn(
        id="n50",
        label="N50",
        type="number",
        path="$.quast.n50",
        sortable=True,
    ),
    OverviewTableColumn(
        id="n_contigs",
        label="#Contigs",
        path="$.quast.n_contigs",
        sortable=True,
    ),
    OverviewTableColumn(
        id="median_cov",
        label="Median cov",
        path="$.postalignqc.median_cov",
        sortable=True,
    ),
    OverviewTableColumn(
        id="n_reads",
        label="# Reads",
        type="number",
        path="$.postalignqc.n_reads",
        sortable=True,
    ),
    OverviewTableColumn(
        id="coverage",
        label="Cov > 10",
        type="number",
        path='$.postalignqc.pct_above_x["10"]',
        sortable=True,
    ),
    OverviewTableColumn(
        id="coverage",
        label="Cov > 30",
        type="number",
        path='$.postalignqc.pct_above_x["30"]',
        sortable=True,
    ),
    OverviewTableColumn(
        id="missing_loci",
        label="# Missing loci",
        type="number",
        path="$.missing_cgmlst_loci",
        sortable=True,
    ),
]

# create combination of valid columns
pred_res_cols = [*VALID_BASE_COLS, *VALID_PREDICTION_COLS]
qc_cols = [*VALID_BASE_COLS, *VALID_QC_COLS]


class GroupInCreate(GroupBase):  # pylint: disable=too-few-public-methods
    """Defines expected input format for groups."""

    table_columns: List[OverviewTableColumn] = Field(description="Columns to display")
    validated_genes: Dict[ElementType, List[str]] | None = Field({})


class GroupInfoDatabase(
    DBModelMixin, ModifiedAtRWModel, GroupInCreate
):  # pylint: disable=too-few-public-methods
    """Defines group info stored in the databas."""


class GroupInfoOut(GroupBase):  # pylint: disable=too-few-public-methods
    """Defines output structure of group info."""
