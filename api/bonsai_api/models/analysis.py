"""Models for creating and managing analysis results from differnt softwares."""
from enum import StrEnum
from typing import Any, Annotated, Literal
from pydantic import BaseModel, Discriminator, Field

from .base import RWModel, UUIDModelMixin, Timestamps, AllowExtraModelMixin

from prp.parse.models.base import ParserOutput as PRPParserOutput
from prp.parse.models.enums import AnalysisType as PrpAnalysisType
from prp.parse.models.enums import AnalysisSoftware as PrpAnalysisSoftware


class ResultStatus(StrEnum):
    PARSED = "parsed"
    EMPTY = "empty"
    ABSENT = "absent"
    SKIPPED = "skipped"
    ERROR = "error"


class Envelope(BaseModel):
    """Storage-friendly envelope (mirrors PRP’s ResultEnvelope)."""
    status: ResultStatus
    value: Any | None = None
    reason: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class AnalysisResult(UUIDModelMixin, Timestamps, AllowExtraModelMixin):
    """Container of analysis results."""

    # meta information
    schema_version: int = 1
    sample_id: str
    software: str
    software_version: str
    pipeline_run_id: str | None = None
    database: str | None = None  # e.g., for AMR databases, cgMLST schemas or kraken DBs

    # results
    envelopes: dict[str, Envelope] = Field(default_factory=dict, description="Formatted analysis result")
    meta: dict[str, Any] = Field(default_factory=dict)

    # created by
    created_by: str | None = None


class CurationAuditBase(RWModel, UUIDModelMixin, Timestamps):
    """Shared curation metadata for both canonical and embedded curation records.

    This base holds the audit and annotation fields common to all curations.
    It does not include storage-specific linking context.
    """

    curated_by: str
    approved_by: str | None = None
    comment: str = Field(default="")
    tags: list[str] = Field(default_factory=list)


class CanonicalCurationBase(CurationAuditBase):
    """Base class for curations stored in the dedicated curation collection.

    These records include sample/analysis context so they can be queried
    independently of the sample embedding.
    """

    sample_id: str = Field(..., description="ID of the sample this curation relates to")
    analysis_id: str = Field(..., description="ID of the analysis this curation applies to")
    analysis_type: str = Field(..., description="Type of analysis (e.g., 'amr', 'typing', 'species_prediction')")


class EmbeddedCurationBase(CurationAuditBase):
    """Base class for curations embedded in sample view documents.

    Embedded curations omit sample/analysis linking context because the
    parent sample and analysis view already provide that information.
    """


class ItemCuration(CanonicalCurationBase):
    """Curation for individual items stored in the canonical curation collection."""

    result_key: str = Field(..., description="Key of the result this curation applies to.")
    
    # Standard decision pattern
    decision: Literal["accept", "reject", "flag_for_review"]
    rejection_reason: str | None = None
    notes: str | None = None


class AnalysisCuration(CanonicalCurationBase):
    """Curation for whole-analysis records stored in the canonical curation collection."""
    
    # Standard decision pattern (different literals per type)
    decision: str  # overridden per subclass
    rejection_reason: str | None = None
    notes: str | None = None


class PhenotypeAnnotation(BaseModel):
    """Annotation of phenotypes related to a variant or gene."""

    name: str
    meta: dict[str, Any] = Field(default_factory=dict)


# Item-level curations
class VariantCuration(ItemCuration):
    """Curation for individual variants stored in the canonical curation collection."""
    annotation_type: Literal["variant"] = "variant"
    
    # Annotations
    phenotypes: list[PhenotypeAnnotation] = Field(default_factory=list)


class GeneCuration(ItemCuration):
    """Curation for detected genes stored in the canonical curation collection."""
    annotation_type: Literal["gene"] = "gene"
    
    # Annotations
    functional_status: str | None = None
    phenotypes: list[PhenotypeAnnotation] = Field(default_factory=list)


# Analysis-level curations
class TypingCuration(AnalysisCuration):
    """Curation for typing results stored in the canonical curation collection."""
    annotation_type: Literal["typing"] = "typing"
    decision: Literal["accept", "reject", "investigate"] = "accept"
    
    epi_type: str | None = None


class SpeciesCuration(AnalysisCuration):
    """Curation for species identification stored in the canonical curation collection."""
    annotation_type: Literal["species_prediction"] = "species_prediction"
    decision: Literal["accept", "reject", "ambiguous"] = "accept"
    
    corrected_species: str | None = None


class QCCuration(AnalysisCuration):
    """Curation for overall sample QC stored in the canonical curation collection."""
    annotation_type: Literal["qc"] = "qc"
    decision: Literal["pass", "fail", "conditional"] = "pass"
    
    conditional_reason: str | None = None


class ItemEmbeddedCuration(EmbeddedCurationBase):
    """Base type for item-level curations embedded in sample views."""

    result_key: str = Field(..., description="Key of the result this curation applies to.")
    decision: Literal["accept", "reject", "flag_for_review"]
    rejection_reason: str | None = None
    notes: str | None = None


class AnalysisEmbeddedCuration(EmbeddedCurationBase):
    """Base type for whole-analysis curations embedded in sample views."""

    decision: str
    rejection_reason: str | None = None
    notes: str | None = None


class EmbeddedVariantCuration(ItemEmbeddedCuration):
    """Denormalized variant curation embedded in sample views."""
    annotation_type: Literal["variant"] = "variant"
    phenotypes: list[PhenotypeAnnotation] = Field(default_factory=list)


class EmbeddedGeneCuration(ItemEmbeddedCuration):
    """Denormalized gene curation embedded in sample views."""
    annotation_type: Literal["gene"] = "gene"
    functional_status: str | None = None
    phenotypes: list[PhenotypeAnnotation] = Field(default_factory=list)


class EmbeddedTypingCuration(AnalysisEmbeddedCuration):
    """Denormalized typing curation embedded in sample views."""
    annotation_type: Literal["typing"] = "typing"
    decision: Literal["accept", "reject", "investigate"] = "accept"
    epi_type: str | None = None


class EmbeddedSpeciesCuration(AnalysisEmbeddedCuration):
    """Denormalized species curation embedded in sample views."""
    annotation_type: Literal["species_prediction"] = "species_prediction"
    decision: Literal["accept", "reject", "ambiguous"] = "accept"
    corrected_species: str | None = None


class EmbeddedQCCuration(AnalysisEmbeddedCuration):
    """Denormalized QC curation embedded in sample views."""
    annotation_type: Literal["qc"] = "qc"
    decision: Literal["pass", "fail", "conditional"] = "pass"
    conditional_reason: str | None = None


CurationRecord = Annotated[
    VariantCuration
    | GeneCuration
    | TypingCuration
    | SpeciesCuration
    | QCCuration,
    Discriminator("annotation_type"),
]

EmbeddedCurationRecord = Annotated[
    EmbeddedVariantCuration
    | EmbeddedGeneCuration
    | EmbeddedTypingCuration
    | EmbeddedSpeciesCuration
    | EmbeddedQCCuration,
    Discriminator("annotation_type"),
]


# ============================================================================
# Input Models for Creating Curations (excludes system-controlled fields)
# ============================================================================


class CurationCreateBase(BaseModel):
    """Base for curation creation requests (no id, timestamps, or approval fields)."""
    comment: str = Field(default="", max_length=5000)
    tags: list[str] = Field(default_factory=list, max_items=20)


class ItemCurationCreateBase(CurationCreateBase):
    """Base for item-level curation creation."""
    result_key: str = Field(..., description="Key of the result this curation applies to.")

    rejection_reason: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)


class AnalysisCurationCreateBase(CurationCreateBase):
    """Base for whole-analysis curation creation."""
    rejection_reason: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)


# Item-level creation models
class VariantCurationCreate(ItemCurationCreateBase):
    """Creation request for variant curation."""
    annotation_type: Literal["variant"] = "variant"
    decision: Literal["accept", "reject", "flag_for_review"]
    phenotypes: list[PhenotypeAnnotation] | None = None


class GeneCurationCreate(ItemCurationCreateBase):
    """Creation request for gene curation."""
    annotation_type: Literal["gene"] = "gene"
    decision: Literal["accept", "reject"]
    functional_status: str | None = None
    phenotypes: list[PhenotypeAnnotation] | None = None


# Analysis-level creation models
class TypingCurationCreate(AnalysisCurationCreateBase):
    """Creation request for typing curation."""
    annotation_type: Literal["typing"] = "typing"
    decision: Literal["accept", "reject", "investigate"]
    epi_type: str | None = None


class SpeciesCurationCreate(AnalysisCurationCreateBase):
    """Creation request for species curation."""
    annotation_type: Literal["species_prediction"] = "species_prediction"
    decision: Literal["accept", "reject", "ambiguous"]
    corrected_species: str | None = None


class QCCurationCreate(AnalysisCurationCreateBase):
    """Creation request for QC curation."""
    annotation_type: Literal["qc"] = "qc"
    decision: Literal["pass", "fail", "conditional"]
    conditional_reason: str | None = None


CurationCreateRecord = Annotated[
    VariantCurationCreate
    | GeneCurationCreate
    | TypingCurationCreate
    | SpeciesCurationCreate
    | QCCurationCreate,
    Discriminator("annotation_type"),
]
