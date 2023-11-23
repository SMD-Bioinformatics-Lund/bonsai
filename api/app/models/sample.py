"""Data model definition of input/ output data"""
from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, Field, conlist

from .base import DBModelMixin, ModifiedAtRWModel, RWModel
from .metadata import RunMetadata
from .phenotype import ElementType, ElementTypeResult, PredictionSoftware
from .qc import QcClassification, QcMethodIndex
from .tags import Tag
from .typing import TypingMethod, TypingResultCgMlst, TypingResultMlst, TypingSoftware

CURRENT_SCHEMA_VERSION = 1
SAMPLE_ID_PATTERN = r"^[a-zA-Z0-9-_]+$"


class TaxLevel(Enum):
    """Taxonomic levels."""

    P = "phylum"
    C = "class"
    O = "order"
    F = "family"
    G = "genus"
    S = "species"


class SpeciesPrediction(RWModel):  # pylint: disable=too-few-public-methods
    """Definition of species prediction results."""

    scientific_name: str
    taxonomy_id: int
    taxonomy_lvl: TaxLevel
    kraken_assigned_reads: int
    added_reads: int
    fraction_total_reads: float


class MethodIndex(RWModel):  # pylint: disable=too-few-public-methods
    """Container for key-value lookup of analytical results."""

    type: ElementType | TypingMethod
    software: PredictionSoftware | TypingSoftware | None
    result: ElementTypeResult | TypingResultMlst | TypingResultCgMlst


class PipelineResult(RWModel):  # pylint: disable=too-few-public-methods
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


class Comment(BaseModel):  # pylint: disable=too-few-public-methods
    """Contianer for comments."""

    username: str = Field(..., min_length=0)
    created_at: datetime = Field(datetime.now())
    comment: str = Field(..., min_length=0)
    displayed: bool = True


class CommentInDatabase(Comment):  # pylint: disable=too-few-public-methods
    """Comment data structure in database."""

    id: int = Field(..., alias="id")


class SampleBase(ModifiedAtRWModel):  # pylint: disable=too-few-public-methods
    """Base datamodel for sample data structure"""

    patient_id: str | None = Field(None)
    tags: List[Tag] = []
    qc_status: QcClassification = QcClassification()
    # comments and non analytic results
    comments: List[CommentInDatabase] = []
    location: str | None = Field(None, description="Location id")
    # signature file name
    genome_signature: str | None = Field(None, description="Genome signature name")


class SampleInCreate(
    SampleBase, PipelineResult
):  # pylint: disable=too-few-public-methods
    """Sample data model used when creating new db entries."""


class SampleInDatabase(
    DBModelMixin, SampleBase, PipelineResult
):  # pylint: disable=too-few-public-methods
    """Sample database model outputed from the database."""


class SampleSummary(
    DBModelMixin, SampleBase, PipelineResult
):  # pylint: disable=too-few-public-methods
    """Summary of a sample stored in the database."""

    major_specie: SpeciesPrediction = Field(...)
