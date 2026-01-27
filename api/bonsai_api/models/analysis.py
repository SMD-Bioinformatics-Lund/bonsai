"""Models for creating and managing analysis results from differnt softwares."""

from enum import StrEnum
from typing import Any, Annotated, Literal
from pydantic import BaseModel, Discriminator, Field

from .base import RecordIdMixin, Timestamps, AllowExtraModelMixin

from prp.parse.models.base import ParserOutput as PRPParserOutput
from prp.parse.models.enums import AnalysisType as PrpAnalysisType
from prp.parse.models.enums import AnalysisSoftware as PrpAnalysisSoftware


class CurrationAnalysisType(StrEnum):
    """Types of analyses or features that can be curated."""

    GENE = "gene"
    QC = "qc"
    SPECIES_PREDICTION = "species_prediction"
    TYPING = "typing"
    VARIANT = "variant"


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


class AnalysisResult(RecordIdMixin, Timestamps, AllowExtraModelMixin):
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


class CurationBase(RecordIdMixin, Timestamps):
    """Base for all curation records."""
    analysis_id: str = Field(description="ID of analysis record being curated.")
    
    # Audit
    curated_by: str
    approved_by: str | None = None
    comment: str = Field(default="")
    tags: list[str] = Field(default_factory=list)


class ItemCuration(CurationBase):
    """Base for item-level curations (variants, genes, etc.)."""
    target_index: int  # which item in the list
    
    # Standard decision pattern
    decision: Literal["accept", "reject", "flag_for_review"]
    rejection_reason: str | None = None
    notes: str | None = None


class AnalysisCuration(CurationBase):
    """Base for whole-analysis curations (typing, species, qc)."""
    
    # Standard decision pattern (different literals per type)
    decision: str  # overridden per subclass
    rejection_reason: str | None = None
    notes: str | None = None


# Item-level curations
class VariantCuration(ItemCuration):
    """Curation for individual variants."""
    analysis_type: Literal["variant"] = "variant"
    decision: Literal["accept", "reject", "flag_for_review"] = "accept"
    
    # Annotations
    phenotype: list[str] | None = None


class GeneCuration(ItemCuration):
    """Curation for detected genes (e.g., AMR genes)."""
    analysis_type: Literal["gene"] = "gene"
    decision: Literal["accept", "reject"] = "accept"
    
    # Annotations
    functional_status: str | None = None
    phenotype: list[str] | None = None


# Analysis-level curations
class TypingCuration(AnalysisCuration):
    """Curation for typing results (MLST, cgMLST, etc.)."""
    analysis_type: Literal["typing"] = "typing"
    decision: Literal["accept", "reject", "investigate"] = "accept"
    
    epi_type: str | None = None


class SpeciesCuration(AnalysisCuration):
    """Curation for species identification."""
    analysis_type: Literal["species_prediction"] = "species_prediction"
    decision: Literal["accept", "reject", "ambiguous"] = "accept"
    
    corrected_species: str | None = None


class QCCuration(AnalysisCuration):
    """Curation for overall sample QC."""
    analysis_type: Literal["qc"] = "qc"
    decision: Literal["pass", "fail", "conditional"] = "pass"
    
    conditional_reason: str | None = None


CurationRecord = Annotated[
    VariantCuration
    | GeneCuration
    | TypingCuration
    | SpeciesCuration
    | QCCuration,
    Discriminator("analysis_type"),
]
