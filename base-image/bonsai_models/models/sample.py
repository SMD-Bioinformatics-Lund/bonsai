"""Data model definition of input/ output data"""

from typing import Literal

from pydantic import Field

from .base import CreatedAt, DBModelMixin, ModifiedAt, MultipleRecordsResponseModel, RWModel
from .metadata import InputMetaEntry, MetaEntryInDb, PipelineInfo, SequencingInfo
from .phenotype import (AMRMethodIndex, StressMethodIndex, VariantBase,
                        VirulenceMethodIndex)
from .qc import QcClassification, QcMethodIndex, SampleQcClassification, VaraintRejectionReason
from .species import SpeciesPrediction, SppMethodIndex
from .tags import TagList
from .typing import (EmmTypingMethodIndex, ResultLineageBase,
                     ShigaTypingMethodIndex, SpatyperTypingMethodIndex,
                     TbProfilerLineage, TypingMethod, TypingResultCgMlst,
                     TypingResultGeneAllele, TypingResultMlst, TypingSoftware)

SCHEMA_VERSION: int = 2

SAMPLE_ID_PATTERN = r"^[a-zA-Z0-9-_]+$"

class MethodIndex(RWModel):
    """Container for key-value lookup of analytical results."""

    type: TypingMethod
    software: TypingSoftware | None
    result: (
        TypingResultMlst
        | TypingResultCgMlst
        | TypingResultGeneAllele
        | TbProfilerLineage
        | ResultLineageBase
        | SpatyperTypingMethodIndex
    )


class SampleBase(RWModel):
    """Base datamodel for sample data structure"""

    sample_id: str = Field(..., alias="sampleId", min_length=3, max_length=100)
    sample_name: str
    lims_id: str

    # metadata
    sequencing: SequencingInfo
    pipeline: PipelineInfo

    # quality
    qc: list[QcMethodIndex] = Field(...)

    # species identification
    species_prediction: list[SppMethodIndex] = Field(..., alias="speciesPrediction")


class ReferenceGenome(RWModel):
    """Reference genome."""

    name: str
    accession: str
    fasta: str
    fasta_index: str | None = None
    genes: str


class IgvAnnotationTrack(RWModel):
    """IGV annotation track data."""

    name: str  # track name to display
    file: str  # path to the annotation file


class PipelineResult(SampleBase):
    """Input format of sample object from pipeline."""

    schema_version: Literal[2] = SCHEMA_VERSION
    # optional typing
    typing_result: list[
        (
            ShigaTypingMethodIndex
            | EmmTypingMethodIndex
            | SpatyperTypingMethodIndex
            | MethodIndex
        )
    ] = Field(..., alias="typingResult")
    # optional phenotype prediction
    element_type_result: list[
        (VirulenceMethodIndex | AMRMethodIndex | StressMethodIndex | MethodIndex)
    ] = Field(..., alias="elementTypeResult")
    # optional variant info
    snv_variants: list[VariantBase] | None = None
    sv_variants: list[VariantBase] | None = None
    indel_variants: list[VariantBase] | None = None
    # optional alignment info
    reference_genome: ReferenceGenome | None = None
    read_mapping: str | None = None
    genome_annotation: list[IgvAnnotationTrack] | None = None


class Comment(CreatedAt):  # pylint: disable=too-few-public-methods
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


class SampleInDb(
    PipelineResult, CreatedAt, ModifiedAt
):  # pylint: disable=too-few-public-methods
    """Base datamodel for sample data structure"""

    tags: TagList = []
    qc_status: QcClassification = QcClassification()
    # comments and non analytic results
    comments: list[CommentInDatabase] = []
    location: str | None = Field(None, description="Location id")
    # signature file name
    genome_signature: str | None = Field(None, description="Genome signature name")
    ska_index: str | None = Field(None, description="Ska index path")


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
    DBModelMixin, PipelineResult
):  # pylint: disable=too-few-public-methods
    """Summary of a sample stored in the database."""

    major_specie: SpeciesPrediction


class MultipleSampleRecordsResponseModel(
    MultipleRecordsResponseModel
):  # pylint: disable=too-few-public-methods
    data: list[SampleInDatabase] = []