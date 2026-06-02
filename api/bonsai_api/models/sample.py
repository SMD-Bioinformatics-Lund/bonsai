"""Data model definition of input/ output data"""

from datetime import datetime
from typing import Any
import logging

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, computed_field, field_validator, model_validator

from prp.parse.models.base import VariantBase
from prp.parse import hydrate_result
from prp.parse.core.registry import get_result_model, _RESULT_MODEL_REGISTRY
from pydantic_core import ValidationError

from bonsai_api.utils import get_timestamp

from .enums import Visibility, ExportStatus, SequencingPlatforms, TypingMethod, ClusterMethod
from .analysis import ResultStatus, EmbeddedCurationRecord
from .pipeline import PipelineRun
from .qc import SampleQcClassification, VaraintRejectionReason
from .tags import Tag
from .base import (
    CreatedAtModelMixin,
    UUIDModelMixin,
    ForbidExtraModelMixin,
    MultipleRecordsResponseModel,
    RWModel,
    Timestamps,
)
from .metadata import InputMetaEntry
from .qc import QcClassification

LOG = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1
SAMPLE_ID_PATTERN = r"^[a-zA-Z0-9-_]+$"


class Comment(CreatedAtModelMixin):  # pylint: disable=too-few-public-methods
    """Contianer for comments."""

    username: str = Field(..., min_length=0)
    comment: str = Field(..., min_length=0)
    displayed: bool = True


class CommentInDatabase(Comment):  # pylint: disable=too-few-public-methods
    """Comment data structure in database."""

    id: int = Field(..., alias="id")


class VariantInDb(VariantBase):
    verified: SampleQcClassification = SampleQcClassification.UNPROCESSED
    reason: VaraintRejectionReason | None = None


class ResfinderVariant(VariantInDb):
    """Container for ResFinder variant information"""


class MykrobeVariant(VariantInDb):
    """Container for Mykrobe variant information"""


class TbProfilerVariant(VariantInDb):
    """Container for TbProfiler variant information"""

    variant_effect: str
    hgvs_nt_change: str | None = Field(..., description="DNA change in HGVS format")
    hgvs_aa_change: str | None = Field(
        ..., description="Protein change in HGVS format"
    )


class SampleBase(Timestamps, ForbidExtraModelMixin):  # pylint: disable=too-few-public-methods
    """Base model for all sample representations.
    
    Contains core sample metadata, tags, and annotations.
    ID hierarchy managed by subclasses:
    - RecordIdMixin provides `id` (internal UUIDv7)
    - External reference via `external_sample_id`
    """

    # Sample metadata
    sample_id: str
    sample_name: str
    lims_id: str | None = None

    # Sample oragnization and classification
    tags: list[Tag] = []
    qc_status: QcClassification = Field(
        default_factory=QcClassification,
        description="Quality control classification of the sample.",
    )

    # Annotations
    comments: list[CommentInDatabase] = Field(default_factory=list)
    location: str | None = Field(None, description="Location id")

    # Data references
    genome_signature: str | None = Field(None, description="Genome signature name")
    ska_index: str | None = Field(None, description="Ska index path")


class MethodIndex(BaseModel):
    """Container for key-value lookup of analytical results."""

    type: str
    software: str | None = None
    result: Any


class SampleInCreate(
    SampleBase
):  # pylint: disable=too-few-public-methods
    """Sample data model used when creating new db entries."""

    groups: list[str] = Field(default_factory=list)
    metadata: list[InputMetaEntry] = Field(default_factory=list)
    element_type_result: list[MethodIndex] = Field(default_factory=list)
    sv_variants: list[VariantInDb] | None = None
    snv_variants: list[VariantInDb] | None = None


# class SampleRecordDb(
#     RecordIdMixin, SampleBase
# ):  # pylint: disable=too-few-public-methods
#     """Sample database model outputed from the database."""

#     metadata: list[MetaEntryInDb] = Field(default_factory=list)
#     element_type_result: list[MethodIndex] = Field(default_factory=list)
#     sv_variants: list[VariantInDb] | None = None
#     snv_variants: list[VariantInDb] | None = None


class InputSearchSimilar(BaseModel):  # pylint: disable=too-few-public-methods
    """Input parameters for finding similar samples."""

    limit: int | None = Field(default=10, ge=1, title="Limit the output to x samples")
    similarity: float = Field(default=0.5, gt=0, le=1, title="Similarity threshold")
    cluster: bool = Field(
        default=False,
        title="Cluster the similar",
        description="If the samples found with similar search should be clustered.",
    )
    narrow_to_sample_ids: list[str] | None = Field(
        default=None,
        description="Restrict the similarity search to these sample IDs. If None, search across all samples.",
        examples=[["sample_id"]],
    )
    typing_method: TypingMethod | None = Field(
        default=None, title="Cluster using a specific typing method"
    )
    cluster_method: ClusterMethod | None = Field(
        default=None, title="Cluster the similar"
    )

    @model_validator(mode="after")
    def validate_cluster_settings(self):
        """Validate that cluster settings are defined if cluster=True."""
        if self.cluster and (self.cluster_method is None or self.typing_method is None):
            raise ValidationError(
                "'cluster_method' and 'typing_method' must be set if 'cluster' is True."
            )
        return self

class InputSamplesSummary(BaseModel):
    """Input parameters for getting sample details."""

    group_id: str | None = None
    sid: list[str] | None = Field(
        None, description="Optional limit query to samples ids"
    )
    fields: list[str] | None = None
    sort: str = "-created_at"
    limit: int | None = Field(default=None, title="Limit the output to x samples")
    offset: int = Field(0, ge=0)


class UpdateSampleInputModel(BaseModel):
    """Input data when updating sample information."""

    typing: list
    phenotype: list

class SampleSummary(
    UUIDModelMixin, SampleBase
):  # pylint: disable=too-few-public-methods
    """Summary of a sample stored in the database."""


class SequencingInfo(ForbidExtraModelMixin):
    """Information on the sample was sequenced."""

    sequencing_run_id: str
    platform: SequencingPlatforms
    instrument: str | None = None
    method: dict[str, str] = Field(default_factory=dict)
    sequenced_at: datetime | None = None


class ReferenceGenome(RWModel):
    """Reference genome."""

    name: str
    accession: str
    fasta: str
    fasta_index: str
    genes: str


class IgvAnnotationTrack(RWModel):
    """IGV annotation track data."""

    name: str  # track name to display
    file: str  # path to the annotation file


class LimsExportStatus(BaseModel):
    """Record of a LIMS export attempt."""

    exported_at: datetime = Field(default_factory=get_timestamp)
    exported_by: str | None = None
    error: str | None = None


class AnalysisViewEntryBase(BaseModel):
    """
    A denormalized, latest-view entry for a (software, analysis_type) result on a sample.

    - `result`: small, normalized object your builder expects under each group array.
    - `summary`: compact fields for overview tables and quick filtering.
    - `status/reason/meta`: envelope transparency.
    - `analysis_id`: pointer to canonical batch for drill-down.
    """

    software: str
    software_version: str
    analysis_type: str

    # optional pointers to the analysis
    analysis_id: str
    pipeline_run_id: str | None = None

    # analysis envelope fields
    status: ResultStatus
    reason: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

    summary: dict[str, Any] = Field(default_factory=dict, description="Compact summary fields for overviews.")


class AnalysisViewEntryDb(AnalysisViewEntryBase):
    """
    A denormalized, latest-view entry for a (software, analysis_type) result on a sample.

    - `result`: small, normalized object your builder expects under each group array.
    - `summary`: compact fields for overview tables and quick filtering.
    - `status/reason/meta`: envelope transparency.
    - `analysis_id`: pointer to canonical batch for drill-down.
    """
    # curation flags
    result: Any
    curations: list[EmbeddedCurationRecord] = Field(
        default_factory=list, 
        description="All denormalized curation records for this analysis embedded in the sample view."
    )


class AnalysisViewEntryOut(AnalysisViewEntryBase):
    """API response model for analysis results."""

    # curation flags
    result: Any
    curations: list[EmbeddedCurationRecord] = Field(
        default_factory=list,
        description="All denormalized curation records for this analysis embedded in the sample view."
    )
    merged_items: list[Any] = Field(
        default_factory=list,
        description="For analyses with item-level results (e.g., variants), a merged list of all items across software, with curation decisions applied. Used for unified display and filtering."
    )

    @computed_field
    @property
    def has_curation(self) -> bool:
        """Whether this analysis has any curation records."""
        return len(self.curations) > 0
    
    @computed_field
    @property
    def curation_status(self) -> str:
        """Overall curation status summary."""
        decisions = {curation.decision for curation in self.curations}
        if "reject" in decisions:
            return "rejected"
        if "ambiguous" in decisions:
            return "ambiguous"
        if "accept" in decisions and len(decisions) == 1:
            return "accepted"
        return "unprocessed"
    
    @field_validator("result", mode="before")
    @classmethod
    def hydrate_result_field(cls, v: Any, info: ValidationInfo) -> BaseModel:
        """Hydrate the result field into the expected model based on analysis_type."""
        analysis_type = info.data.get("analysis_type")
        software = info.data.get("software")

        try:
            return hydrate_result(result=v, analysis_type=analysis_type, software=software)
        except Exception as exc:
            LOG.warning("Failed to hydrate result for %s/%s: %s", software, analysis_type, exc)
            return v
    
    # def model_post_init(self, __context):
    #     # Called after the model is fully created
    #     self.merged_items = merge_items_with_curations(
    #         self.result,
    #         self.curations
    #     )


class SampleInfoCreate(ForbidExtraModelMixin):  # pylint: disable=too-few-public-methods
    """Defines output structure of group info used for creation."""

    sample_id: str | None = None
    sample_name: str
    lims_id: str | None = None

    groups: list[str] = Field(default_factory=list, description="Group ids")

    sequencing: SequencingInfo | None = None
    metadata: list[InputMetaEntry] = Field(default_factory=list)

    # preparation for role based access controll
    owners: list[str] = Field(default_factory=list, description="Owner identifiers (user:<id>)")
    owner_organizations: list[str] = Field(default_factory=list, description="Organization ids (org:<id>)")
    access_groups: list[str] = Field(default_factory=list, description="Optional access groups")
    visibility: Visibility = Visibility.PUBLIC


class SampleRecordDb(SampleBase):
    """Database representation of a sample."""

    # IDs
    external_sample_id: str = Field(..., description="Id from other systems used to reference the sample.")

    # Access control
    owners: list[str] = Field(default_factory=list, description="Owner identifiers (user:<id>)")
    owner_organizations: list[str] = Field(default_factory=list, description="Organization ids (org:<id>)")
    access_groups: list[str] = Field(default_factory=list, description="Optional access groups")
    visibility: Visibility = Visibility.PUBLIC

    # Grouping and organization
    groups: list[str] = Field(default_factory=list, description="Group Ids the sample is a member of.")
    metadata: list[InputMetaEntry] = []

    # Curation flag
    curated: bool = False

    # Sequencing and pipeline information
    sequencing: SequencingInfo | None = None
    pipeline_runs: list[PipelineRun] = Field(default_factory=list)
    last_pipeline_run_id: str | None = None

    # Analysis results
    qc_result: list[AnalysisViewEntryDb] = Field(default_factory=list)
    species_prediction: list[AnalysisViewEntryDb] = Field(default_factory=list)
    typing_result: list[AnalysisViewEntryDb] = Field(default_factory=list)
    element_type_result: list[AnalysisViewEntryDb] = Field(default_factory=list)

    # Reference and annotation
    genomic_asset_ids: list[str] = Field(
        default_factory=list,
        description="Associated genomic asset sets"
    )
    latest_genomic_asset_id: str | None = None


    reference_genome: ReferenceGenome | None = None
    read_mapping: str | None = None
    genome_annotation: list[IgvAnnotationTrack] | None = None

    # LIMS export tracking
    lims_export_status: ExportStatus = ExportStatus.NOT_EXPORTED
    lims_exports: list[LimsExportStatus] = Field(default_factory=list)


class SampleRecordOut(SampleBase):
    """API output model for samples (excludes internal history fields)."""

    model_config = ConfigDict(extra='ignore')
    
    # IDs
    external_sample_id: str = Field(..., description="Id from other systems used to reference the sample.")
    
    # Access control
    owners: list[str] = Field(default_factory=list)
    owner_organizations: list[str] = Field(default_factory=list)
    access_groups: list[str] = Field(default_factory=list)
    visibility: Visibility = Visibility.PUBLIC
    
    # Grouping and organization
    groups: list[str] = Field(default_factory=list)
    metadata: list[InputMetaEntry] = []
    
    # Sequencing and pipeline information
    sequencing: SequencingInfo | None = None
    pipeline: PipelineRun | None = None
    
    # Analysis results
    qc_result: list[AnalysisViewEntryOut] = Field(default_factory=list)
    species_prediction: list[AnalysisViewEntryOut] = Field(default_factory=list)
    typing_result: list[AnalysisViewEntryOut] = Field(default_factory=list)
    element_type_result: list[AnalysisViewEntryOut] = Field(default_factory=list)
    
    # Reference and annotation
    reference_genome: ReferenceGenome | None = None
    read_mapping: str | None = None
    genome_annotation: list[IgvAnnotationTrack] | None = None
    
    # LIMS tracking
    lims_export_status: ExportStatus = ExportStatus.NOT_EXPORTED


class MultipleSampleRecordsResponseModel(
    MultipleRecordsResponseModel
):  # pylint: disable=too-few-public-methods
    data: list[SampleRecordOut] = []