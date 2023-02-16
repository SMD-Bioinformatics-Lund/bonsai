"""Data model definition of input/ output data"""
from datetime import datetime
from enum import Enum
from typing import Dict, List

from pydantic import BaseModel, Field, conlist

from .base import DBModelMixin, ModifiedAtRWModel, RWModel
from .tags import Tag

from .metadata import RunMetadata
from .phenotype import PhenotypeResult, PhenotypeResultIndex
from .qc import QcMethodIndex
from .typing import TypingResultIndex, TypingResultCgMlst, TypingResultMlst

SAMPLE_ID_PATTERN = "^[a-zA-Z0-9-_]+$"
# , regex=SAMPLE_ID_PATTERN


class TaxLevel(Enum):
    P = "phylum"
    C = "class"
    O = "order"
    F = "family"
    G = "genus"
    S = "specie"


class SpeciesPrediction(RWModel):
    scientific_name: str = Field(..., alias="scientificName")
    taxonomy_id: int = Field(..., alias="taxonomyId")
    taxonomy_lvl: TaxLevel = Field(..., alias="taxonomyLevel")
    kraken_assigned_reads: int = Field(..., alias="krakenAssignedReads")
    added_reads: int = Field(..., alias="addedReads")
    fraction_total_reads: float = Field(..., alias="fractionTotalReads")


class PipelineResult(RWModel):
    """Input format of sample object from pipeline."""

    sample_id: str = Field(..., alias="sampleId", min_length=3, max_length=100)
    schema_version: int = Field(..., alias="schemaVersion", gt=0)

    # mandatory metadata fields
    run_metadata: RunMetadata = Field(..., alias="runMetadata")
    species_prediction: conlist(SpeciesPrediction, min_items=1) = Field(
        ..., alias="speciesPrediction"
    )

    # optional fields
    qc: List[QcMethodIndex] = Field(...)
    typing_result: List[TypingResultIndex] = Field(..., alias="typingResult")
    phenotype_result: List[PhenotypeResultIndex] = Field(..., alias="phenotypeResult")


class Comment(BaseModel):
    """Contianer for comments."""

    username: str = Field(..., min_length=0)
    created_at: datetime = Field(datetime.now(), alias="createdAt")
    comment: str = Field(..., min_length=0)
    displayed: bool = True


class CommentInDatabase(Comment):
    """Comment data structure in database."""

    id: int = Field(..., alias="id")


class SampleBase(ModifiedAtRWModel):
    """Base datamodel for sample data structure"""

    patient_id: str | None = Field(None, alias="patientId")
    # comments and non analytic results
    comments: List[CommentInDatabase] = []
    location: str | None = Field(None, description="Location id")


class SampleInCreate(SampleBase, PipelineResult):
    """Sample data model used when creating new db entries."""

    pass


class SampleInDatabase(DBModelMixin, SampleBase, PipelineResult):
    """Sample database model outputed from the database."""

    pass


class SampleSummary(DBModelMixin, SampleBase, PipelineResult):
    """Summary of a sample stored in the database."""

    major_specie: SpeciesPrediction = Field(..., alias="majorSpecie")
