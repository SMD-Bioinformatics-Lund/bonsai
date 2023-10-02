"""Data model definition of input/ output data"""
from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, Field, conlist

from .base import DBModelMixin, ModifiedAtRWModel, RWModel
from .tags import Tag

from .metadata import RunMetadata
from .phenotype import ElementTypeResult, ElementType, PredictionSoftware
from .qc import QcMethodIndex, QcClassification
from .typing import TypingMethod, TypingResultCgMlst, TypingResultMlst, TypingSoftware

CURRENT_SCHEMA_VERSION = 1
SAMPLE_ID_PATTERN = r"^[a-zA-Z0-9-_]+$"
# , regex=SAMPLE_ID_PATTERN


class TaxLevel(Enum):
    P = "phylum"
    C = "class"
    O = "order"
    F = "family"
    G = "genus"
    S = "species"


class SpeciesPrediction(RWModel):
    scientific_name: str
    taxonomy_id: int
    taxonomy_lvl: TaxLevel
    kraken_assigned_reads: int
    added_reads: int
    fraction_total_reads: float


class MethodIndex(RWModel):
    """Container for key-value lookup of analytical results."""

    type: ElementType | TypingMethod
    software: PredictionSoftware | TypingSoftware | None
    result: ElementTypeResult | TypingResultMlst | TypingResultCgMlst


class PipelineResult(RWModel):
    """Input format of sample object from pipeline."""

    sample_id: str = Field(..., min_length=3, max_length=100)
    schema_version: int = Field(..., eq=CURRENT_SCHEMA_VERSION)

    # mandatory metadata fields
    run_metadata: RunMetadata
    species_prediction: conlist(SpeciesPrediction, min_length=1)

    # optional fields
    qc: List[QcMethodIndex] = Field(...)
    typing_result: List[MethodIndex] = Field(...)
    element_type_result: List[MethodIndex] = Field(...)


class Comment(BaseModel):
    """Contianer for comments."""

    username: str = Field(..., min_length=0)
    created_at: datetime = Field(datetime.now())
    comment: str = Field(..., min_length=0)
    displayed: bool = True


class CommentInDatabase(Comment):
    """Comment data structure in database."""

    id: int = Field(..., alias="id")


class SampleBase(ModifiedAtRWModel):
    """Base datamodel for sample data structure"""

    patient_id: str | None = Field(None)
    tags: List[Tag] = []
    qc_status: QcClassification = QcClassification()
    # comments and non analytic results
    comments: List[CommentInDatabase] = []
    location: str | None = Field(None, description="Location id")
    # signature file name
    genome_signature: str | None = Field(None, description="Genome signature name")


class SampleInCreate(SampleBase, PipelineResult):
    """Sample data model used when creating new db entries."""

    pass


class SampleInDatabase(DBModelMixin, SampleBase, PipelineResult):
    """Sample database model outputed from the database."""

    pass


class SampleSummary(DBModelMixin, SampleBase, PipelineResult):
    """Summary of a sample stored in the database."""

    major_specie: SpeciesPrediction = Field(...)
