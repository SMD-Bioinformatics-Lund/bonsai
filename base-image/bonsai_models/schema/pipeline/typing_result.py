"""Typing related data models"""

from typing import Any, Literal

from pydantic import Field

from bonsai_models.base import ApiModel
from .constants import (ChewbbacaErrors, MlstErrors, TypingMethod,
                        TypingSoftware)
from .phenotype import SerotypeGene, VirulenceGene


class ResultMlstBase(ApiModel):
    """Base class for storing MLST-like typing results"""

    alleles: dict[str, int | str | list[Any] | None]


class TypingResultMlst(ResultMlstBase):
    """MLST results"""

    scheme: str
    sequence_type: int | None = Field(None, alias="sequenceType")


class TypingResultCgMlst(ResultMlstBase):
    """MLST results"""

    n_novel: int = Field(0, alias="nNovel")
    n_missing: int = Field(0, alias="nNovel")


class TypingResultShiga(ApiModel):
    """Container for shigatype gene information"""

    rfb: str | None = None
    rfb_hits: float | None = None
    mlst: str | None = None
    flic: str | None = None
    crispr: str | None = None
    ipah: str | None = None
    predicted_serotype: str | None = None
    predicted_flex_serotype: str | None = None
    comments: str | None = None


class ShigaTypingMethodIndex(ApiModel):
    """Method Index Shiga."""

    type: Literal[TypingMethod.SHIGATYPE]
    software: Literal[TypingSoftware.SHIGAPASS]
    result: TypingResultShiga


class TypingResultEmm(ApiModel):
    """Container for emmtype gene information"""

    cluster_count: int
    emmtype: str | None = None
    emm_like_alleles: list[str] | None = None
    emm_cluster: str | None = None


class EmmTypingMethodIndex(ApiModel):
    """Method Index Emm."""

    type: Literal[TypingMethod.EMMTYPE]
    software: Literal[TypingSoftware.EMMTYPER]
    result: TypingResultEmm


class ResultLineageBase(ApiModel):
    """Lineage results"""

    lineage_depth: float | None = None
    main_lineage: str
    sublineage: str


class LineageInformation(ApiModel):
    """Base class for storing lineage information typing results"""

    lineage: str | None
    family: str | None
    rd: str | None
    fraction: float | None
    support: list[dict[str, Any]] | None = None


class TbProfilerLineage(ResultLineageBase):
    """Base class for storing MLST-like typing results"""

    lineages: list[LineageInformation]


class TypingResultGeneAllele(VirulenceGene, SerotypeGene):
    """Identification of individual gene alleles."""


CgmlstAlleles = dict[str, (int | None | ChewbbacaErrors | MlstErrors | list[int])]


class TypingResultSpatyper(ApiModel):
    """Spatyper results"""

    sequence_name: str | None
    repeats: str | None
    type: str | None


class SpatyperTypingMethodIndex(ApiModel):
    """Method Index Spatyper."""

    type: Literal[TypingMethod.SPATYPE]
    software: Literal[TypingSoftware.SPATYPER]
    result: TypingResultSpatyper
