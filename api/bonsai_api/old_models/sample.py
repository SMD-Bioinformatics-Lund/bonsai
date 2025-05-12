"""Data model definition of input/ output data"""

from typing import Optional, Union

from bonsai_models.models.phenotype import (
    AmrFinderGene,
    AmrFinderResistanceGene,
    ElementType,
    PredictionSoftware,
    ResfinderGene,
    VariantBase,
    VirulenceGene,
)
from bonsai_models.models.sample import PipelineResult
from bonsai_models.models.species import SpeciesPrediction
from bonsai_models.models.typing import (
    ResultLineageBase,
    TbProfilerLineage,
    TypingMethod,
    TypingResultCgMlst,
    TypingResultGeneAllele,
    TypingResultMlst,
    TypingSoftware,
)
from pydantic import BaseModel, Field

from ..models.qc import SampleQcClassification, VaraintRejectionReason
from ..models.tags import Tag
from .base import (
    DateTimeModelMixin,
    DBModelMixin,
    ModifiedAtRWModel,
    MultipleRecordsResponseModel,
)
from .metadata import InputMetaEntry, MetaEntryInDb
from .qc import QcClassification

CURRENT_SCHEMA_VERSION = 1
SAMPLE_ID_PATTERN = r"^[a-zA-Z0-9-_]+$"


class Comment(DateTimeModelMixin):  # pylint: disable=too-few-public-methods
    """Contianer for comments."""

    username: str = Field(..., min_length=0)
    comment: str = Field(..., min_length=0)
    displayed: bool = True


class CommentInDatabase(Comment):  # pylint: disable=too-few-public-methods
    """Comment data structure in database."""

    id: int = Field(..., alias="id")


class VariantInDb(VariantBase):
    verified: SampleQcClassification = SampleQcClassification.UNPROCESSED
    reason: Optional[VaraintRejectionReason] = None


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

    tags: list[Tag] = []
    qc_status: QcClassification = QcClassification()
    # comments and non analytic results
    comments: list[CommentInDatabase] = []
    location: str | None = Field(None, description="Location id")
    # signature file name
    genome_signature: str | None = Field(None, description="Genome signature name")
    ska_index: str | None = Field(None, description="Ska index path")


class ElementTypeResult(BaseModel):
    """Phenotype result data model.

    A phenotype result is a generic data structure that stores predicted genes,
    mutations and phenotyp changes.
    """

    phenotypes: dict[str, list[str]]
    genes: list[
        Union[AmrFinderResistanceGene, AmrFinderGene, ResfinderGene, VirulenceGene]
    ]
    variants: list[Union[TbProfilerVariant, MykrobeVariant, ResfinderVariant]]


class MethodIndex(BaseModel):
    """Container for key-value lookup of analytical results."""

    type: Union[ElementType, TypingMethod]
    software: PredictionSoftware | TypingSoftware | None
    result: Union[
        ElementTypeResult,
        TypingResultMlst,
        TypingResultCgMlst,
        TypingResultGeneAllele,
        TbProfilerLineage,
        ResultLineageBase,
    ]


class SampleInCreate(
    SampleBase, PipelineResult
):  # pylint: disable=too-few-public-methods
    """Sample data model used when creating new db entries."""

    metadata: list[InputMetaEntry] = []
    element_type_result: list[MethodIndex]
    sv_variants: list[VariantInDb] | None = None
    snv_variants: list[VariantInDb] | None = None


class SampleInDatabase(
    DBModelMixin, SampleBase, PipelineResult
):  # pylint: disable=too-few-public-methods
    """Sample database model outputed from the database."""

    metadata: list[MetaEntryInDb] = []
    element_type_result: list[MethodIndex]
    sv_variants: list[VariantInDb] | None = None
    snv_variants: list[VariantInDb] | None = None


class SampleSummary(
    DBModelMixin, SampleBase, PipelineResult
):  # pylint: disable=too-few-public-methods
    """Summary of a sample stored in the database."""

    major_specie: SpeciesPrediction = Field(...)


class MultipleSampleRecordsResponseModel(
    MultipleRecordsResponseModel
):  # pylint: disable=too-few-public-methods
    data: list[SampleInDatabase] = []
