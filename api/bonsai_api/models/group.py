"""Routes related to collections of samples."""

from typing import Dict, List, Literal
from datetime import datetime

from prp.models.phenotype import ElementType
from pydantic import BaseModel, ConfigDict, Field

from .base import DBModelMixin, ModifiedAtRWModel, ObjectId, RWModel
from .sample import SampleSummary
from bonsai_api.utils import get_timestamp

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


class SampleTableColumnInput(BaseModel):  # pylint: disable=too-few-public-methods
    """Definition of how to display and function of overview table."""

    id: str = Field(..., description="Column id")
    label: str = Field(..., description="Display name")
    path: str = Field(..., description="JSONpath describing how to access the data")
    type: Literal["string", "number", "date", "boolean", "list", "custom"] = "string"
    source: Literal["static", "metadata"] = "static"  # where the columns are predefined or relate to metadata
    renderer: str | None = None
    sortable: bool = False
    filterable: bool = False


class SampleTableColumnDB(SampleTableColumnInput):  # pylint: disable=too-few-public-methods
    """Database representation of a column."""

    created_at: datetime = Field(default_factory=get_timestamp)
    modified_at: datetime = Field(default_factory=get_timestamp)


VALID_BASE_COLS: list[SampleTableColumnInput] = [
    SampleTableColumnInput(
        id="sample_btn",
        label="",
        type="custom",
        renderer="sample_btn_renderer",
        path="$.sample_id",
    ),
    SampleTableColumnInput(
        id="sample_id",
        label="Sample Id",
        path="$.sample_id",
        sortable=True,
    ),
]

# Prediction result columns
VALID_PREDICTION_COLS: list[SampleTableColumnInput] = [
    SampleTableColumnInput(
        id="sample_name",
        label="Name",
        path="$.sample_name",
        sortable=True,
    ),
    SampleTableColumnInput(
        id="lims_id",
        label="LIMS id",
        path="$.lims_id",
        sortable=True,
    ),
    SampleTableColumnInput(
        id="assay",
        label="Assay",
        path="$.assay",
        sortable=True,
    ),
    SampleTableColumnInput(
        id="release_life_cycle",
        label="Release life cycle",
        path="$.release_life_cycle",
        sortable=True,
    ),
    SampleTableColumnInput(
        id="sequencing_run",
        label="Sequencing run",
        path="$.sequencing_run",
        sortable=True,
    ),
    SampleTableColumnInput(
        id="taxonomic_name",
        label="Major species",
        renderer="taxonomic_name_renderer",
        path="$.species_prediction.scientific_name",
        sortable=True,
    ),
    SampleTableColumnInput(
        id="qc",
        label="QC",
        type="custom",
        path="$.qc_status",
        sortable=True,
        renderer="qc_status_renderer",
    ),
    SampleTableColumnInput(
        id="profile",
        label="Analysis profile",
        path="$.profile",
        type="list",
        sortable=True,
        filterable=True,
    ),
    SampleTableColumnInput(
        id="comments",
        label="Comments",
        type="custom",
        path="$.comments",
        renderer="comments_renderer",
    ),
    SampleTableColumnInput(
        id="tags",
        label="Tags",
        type="custom",
        path="$.tags",
        renderer="tags_renderer",
    ),
    SampleTableColumnInput(
        id="mlst",
        label="MLST ST",
        path="$.mlst",
        sortable=True,
        filterable=True,
    ),
    SampleTableColumnInput(
        id="stx",
        label="STX typing",
        path="$.stx",
        sortable=True,
        filterable=True,
    ),
    SampleTableColumnInput(
        id="oh",
        label="OH typing",
        path="$.oh_type",
        sortable=True,
        filterable=True,
    ),
    SampleTableColumnInput(
        id="cdate",
        label="Date",
        type="date",
        path="$.created_at",
        sortable=True,
    ),
]

# Prediction result columns
VALID_QC_COLS = [
    SampleTableColumnInput(
        id="sample_name",
        label="Name",
        path="$.sample_name",
        sortable=True,
    ),
    SampleTableColumnInput(
        id="sequencing_run",
        label="Sequencing run",
        path="$.sequencing_run",
        sortable=True,
    ),
    SampleTableColumnInput(
        id="qc",
        label="QC",
        type="custom",
        path="$.qc_status.status",
        sortable=True,
    ),
    SampleTableColumnInput(
        id="n50",
        label="N50",
        type="number",
        path="$.quast.n50",
        sortable=True,
    ),
    SampleTableColumnInput(
        id="n_contigs",
        label="#Contigs",
        path="$.quast.n_contigs",
        sortable=True,
    ),
    SampleTableColumnInput(
        id="median_cov",
        label="Median cov",
        path="$.postalignqc.median_cov",
        sortable=True,
    ),
    SampleTableColumnInput(
        id="n_reads",
        label="# Reads",
        type="number",
        path="$.postalignqc.n_reads",
        sortable=True,
    ),
    SampleTableColumnInput(
        id="pct_cov_over_10",
        label="Cov > 10",
        type="number",
        path='$.postalignqc.pct_above_x["10"]',
        sortable=True,
    ),
    SampleTableColumnInput(
        id="pct_cov_over_30",
        label="Cov > 30",
        type="number",
        path='$.postalignqc.pct_above_x["30"]',
        sortable=True,
    ),
    SampleTableColumnInput(
        id="cgmlst_missing_loci",
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

    table_columns: List[SampleTableColumnInput] = Field(description="Columns to display")
    validated_genes: Dict[ElementType, List[str]] | None = Field({})


class GroupInfoDatabase(
    DBModelMixin, ModifiedAtRWModel, GroupInCreate
):  # pylint: disable=too-few-public-methods
    """Defines group info stored in the databas."""


class GroupInfoOut(GroupBase):  # pylint: disable=too-few-public-methods
    """Defines output structure of group info."""
