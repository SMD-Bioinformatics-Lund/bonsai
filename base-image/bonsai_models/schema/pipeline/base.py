"""Pipeline results."""

from typing import Generic, Literal, TypeVar
from pydantic import BaseModel, Field

from bonsai_models.base import ApiModel
from bonsai_models.schema.pipeline.constants import TypingMethod, TypingSoftware
from .metadata import PipelineInfo, SequencingInfo
from .phenotype import (AMRMethodIndex, StressMethodIndex, VariantBase,
                       VirulenceMethodIndex)
from .qc import QcMethodIndex
from .species import SppMethodIndex
from .typing_result import (EmmTypingMethodIndex, ResultLineageBase,
                           ShigaTypingMethodIndex, SpatyperTypingMethodIndex,
                           TbProfilerLineage, TypingResultCgMlst, TypingResultEmm,
                           TypingResultGeneAllele, TypingResultMlst, TypingResultSpatyper)


TType = TypeVar("TType")
TSoftware = TypeVar("TSoftware")
TResult = TypeVar("TResult")


class ResultIndexBase(BaseModel, Generic[TType, TSoftware, TResult]):
    """Container for key-value lookup of analytical results."""

    type: TType
    software: TSoftware | None
    result: TResult


CgmlstResultIndex = ResultIndexBase[
    Literal[TypingMethod.CGMLST],
    Literal[TypingSoftware.CHEWBBACA],
    TypingResultCgMlst
]

MlstResultIndex = ResultIndexBase[
    Literal[TypingMethod.MLST],
    Literal[TypingSoftware.MLST],
    TypingResultMlst
]

LineageResultIndex = ResultIndexBase[
    Literal[TypingMethod.LINEAGE],
    Literal[TypingSoftware.TBPROFILER],
    TbProfilerLineage
]

SpatyperResultIndex = ResultIndexBase[
    Literal[TypingMethod.SPATYPE],
    Literal[TypingSoftware.SPATYPER],
    TypingResultSpatyper
]

EmmResultIndex = ResultIndexBase[
    Literal[TypingMethod.EMMTYPE],
    Literal[TypingSoftware.EMMTYPER],
    TypingResultEmm
]

class MethodIndex(ApiModel):
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


class IgvAnnotationTrack(ApiModel):
    """IGV annotation track data."""

    name: str  # track name to display
    file: str  # path to the annotation file


class ReferenceGenome(ApiModel):
    """Reference genome."""

    name: str
    accession: str
    fasta: str
    fasta_index: str | None = None
    genes: str


class PipelineResult(ApiModel):
    """Input format of sample object from pipeline."""

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
