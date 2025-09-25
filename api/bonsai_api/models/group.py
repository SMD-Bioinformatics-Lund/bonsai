"""Routes related to collections of samples."""

from typing import Dict, List, Literal

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


class SampleTableColumnInput(BaseModel):  # pylint: disable=too-few-public-methods
    """Definition of how to display and function of overview table."""

    id: str = Field(..., description="Column id")
    label: str = Field(..., description="Display name")
    path: str = Field(..., description="JSONpath describing how to access the data")
    type: Literal["string", "number", "date", "boolean", "list", "custom"] = "string"
    source: Literal["static", "metadata"] = (
        "static"  # where the columns are predefined or relate to metadata
    )
    renderer: str | None = None
    visible: bool = True
    sortable: bool = True
    searchable: bool = True


class SampleTableColumnDB(BaseModel):  # pylint: disable=too-few-public-methods
    """Database representation of a column."""

    id: str = Field(..., description="Column id")
    visible: bool = True
    sortable: bool = True
    searchable: bool = True


VALID_BASE_COLS: list[SampleTableColumnInput] = [
    SampleTableColumnInput(
        id="sample_btn",
        label="",
        type="custom",
        renderer="sample_btn_renderer",
        path="$.sample_id",
        sortable=False,
        searchable=False,
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
        id="qc_status",
        label="QC",
        type="custom",
        path="$.qc_status",
        sortable=True,
        renderer="qc_status_renderer",
    ),
    SampleTableColumnInput(
        id="analysis_profile",
        label="Analysis profile",
        path="$.profile",
        type="list",
        sortable=True,
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
        id="mlst_typing",
        label="MLST ST",
        path="$.mlst",
        sortable=True,
    ),
    SampleTableColumnInput(
        id="stx_typing",
        label="STX typing",
        path="$.stx",
        sortable=True,
    ),
    SampleTableColumnInput(
        id="oh_typing",
        label="OH typing",
        path="$.oh_type",
        sortable=True,
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
        id="qc_status",
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


DEFAULT_COLUMNS: list[str] = [
    "sample_btn",
    "sample_id",
    "sample_name",
    "tags",
    "assay",
    "taxonomic_name",
    "qc_status",
    "comments",
    "cdate",
]

# create combination of valid columns
pred_res_cols = [*VALID_BASE_COLS, *VALID_PREDICTION_COLS]
qc_cols = [*VALID_BASE_COLS, *VALID_QC_COLS]

SCHEMA_VERSION: str = "1"


class GroupInCreate(GroupBase):  # pylint: disable=too-few-public-methods
    """Defines expected input format for groups."""

    schema_version: str = Field(
        default=SCHEMA_VERSION, description="Version of the group schema."
    )
    table_columns: list[SampleTableColumnDB] = Field(
        default=[], description="IDs of columns to display."
    )
    # table_columns: list[SampleTableColumnInput] = Field(default=[], description="IDs of columns to display.")
    validated_genes: dict[ElementType, list[str]] | None = {}


class GroupInfoDatabase(
    DBModelMixin, ModifiedAtRWModel, GroupInCreate
):  # pylint: disable=too-few-public-methods
    """Defines group info stored in the databas."""


class GroupInfoOut(GroupBase):  # pylint: disable=too-few-public-methods
    """Defines output structure of group info."""

    table_columns: list[str] = Field(
        default=[], description="IDs of columns to display."
    )
