"""Data model definition of input/ output data"""
from datetime import datetime
from typing import List, Dict, Union, Optional

from prp.models import PipelineResult
from prp.models.species import SpeciesPrediction
from prp.models.phenotype import VariantBase, AmrFinderResistanceGene, AmrFinderGene, ResfinderGene, VirulenceGene, ElementType, PredictionSoftware
from prp.models.typing import (
    TypingMethod,
    TypingResultCgMlst,
    TypingResultGeneAllele,
    TypingResultLineage,
    TypingResultMlst,
    TypingSoftware,
)
from pydantic import BaseModel, Field

from ..models.tags import Tag
from ..models.qc import  SampleQcClassification
from .base import DBModelMixin, ModifiedAtRWModel
from .qc import QcClassification

CURRENT_SCHEMA_VERSION = 1
SAMPLE_ID_PATTERN = r"^[a-zA-Z0-9-_]+$"


class Comment(BaseModel):  # pylint: disable=too-few-public-methods
    """Contianer for comments."""

    username: str = Field(..., min_length=0)
    created_at: datetime = Field(datetime.now())
    comment: str = Field(..., min_length=0)
    displayed: bool = True


class CommentInDatabase(Comment):  # pylint: disable=too-few-public-methods
    """Comment data structure in database."""

    id: int = Field(..., alias="id")


class VariantInDb(VariantBase):
    verified: SampleQcClassification = SampleQcClassification.UNPROCESSED
    reason: Optional[str] = None


class ResfinderVariant(VariantInDb):
    """Container for ResFinder variant information"""


class MykrobeVariant(VariantInDb):
    """Container for Mykrobe variant information"""


class TbProfilerVariant(VariantInDb):
    """Container for TbProfiler variant information"""

    variant_effect: str
    hgvs_nt_change: Optional[str] = Field(..., description="DNA change in HGVS format")
    hgvs_aa_change: Optional[str] = Field(
        ..., description="Protein change in HGVS format"
    )


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


class ElementTypeResult(BaseModel):
    """Phenotype result data model.

    A phenotype result is a generic data structure that stores predicted genes,
    mutations and phenotyp changes.
    """

    phenotypes: Dict[str, List[str]]
    genes: List[Union[AmrFinderResistanceGene, AmrFinderGene, ResfinderGene, VirulenceGene]]
    variants: List[Union[TbProfilerVariant, MykrobeVariant, ResfinderVariant]]


class MethodIndex(BaseModel):
    """Container for key-value lookup of analytical results."""

    type: Union[ElementType, TypingMethod]
    software: PredictionSoftware | TypingSoftware | None
    result: Union[
        ElementTypeResult,
        TypingResultMlst,
        TypingResultCgMlst,
        TypingResultLineage,
        TypingResultGeneAllele,
    ]



class SampleInCreate(
    SampleBase, PipelineResult
):  # pylint: disable=too-few-public-methods
    """Sample data model used when creating new db entries."""

    element_type_result: List[MethodIndex]

class SampleInDatabase(
    DBModelMixin, SampleBase, PipelineResult
):  # pylint: disable=too-few-public-methods
    """Sample database model outputed from the database."""

    element_type_result: List[MethodIndex]


class SampleSummary(
    DBModelMixin, SampleBase, PipelineResult
):  # pylint: disable=too-few-public-methods
    """Summary of a sample stored in the database."""

    major_specie: SpeciesPrediction = Field(...)