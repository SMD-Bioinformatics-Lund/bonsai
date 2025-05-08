"""Typing related data models"""

from enum import Enum
from typing import Any, Literal

from pydantic import Field

from .base import RWModel
from .phenotype import SerotypeGene, VirulenceGene


class TypingSoftware(str, Enum):
    """Container for software names."""

    CHEWBBACA = "chewbbaca"
    MLST = "mlst"
    TBPROFILER = "tbprofiler"
    MYKROBE = "mykrobe"
    VIRULENCEFINDER = "virulencefinder"
    SEROTYPEFINDER = "serotypefinder"
    SHIGAPASS = "shigapass"
    EMMTYPER = "emmtyper"
    SPATYPER = "spatyper"


class TypingMethod(str, Enum):
    """Valid typing methods."""

    MLST = "mlst"
    CGMLST = "cgmlst"
    LINEAGE = "lineage"
    STX = "stx"
    OTYPE = "O_type"
    HTYPE = "H_type"
    SHIGATYPE = "shigatype"
    EMMTYPE = "emmtype"
    SPATYPE = "spatype"


class ChewbbacaErrors(str, Enum):
    """Chewbbaca error codes."""

    PLOT5 = "PLOT5"
    PLOT3 = "PLOT3"
    LOTSC = "LOTSC"
    NIPH = "NIPH"
    NIPHEM = "NIPHEM"
    ALM = "ALM"
    ASM = "ASM"
    LNF = "LNF"
    EXC = "EXC"
    PAMA = "PAMA"


class MlstErrors(str, Enum):
    """MLST error codes."""

    NOVEL = "novel"
    PARTIAL = "partial"


class ResultMlstBase(RWModel):
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


class TypingResultShiga(RWModel):
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


class ShigaTypingMethodIndex(RWModel):
    """Method Index Shiga."""

    type: Literal[TypingMethod.SHIGATYPE]
    software: Literal[TypingSoftware.SHIGAPASS]
    result: TypingResultShiga


class TypingResultEmm(RWModel):
    """Container for emmtype gene information"""

    cluster_count: int
    emmtype: str | None = None
    emm_like_alleles: list[str] | None = None
    emm_cluster: str | None = None


class EmmTypingMethodIndex(RWModel):
    """Method Index Emm."""

    type: Literal[TypingMethod.EMMTYPE]
    software: Literal[TypingSoftware.EMMTYPER]
    result: TypingResultEmm


class ResultLineageBase(RWModel):
    """Lineage results"""

    lineage_depth: float | None = None
    main_lineage: str
    sublineage: str


class LineageInformation(RWModel):
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


CgmlstAlleles = dict[str, (
    int | None | ChewbbacaErrors | MlstErrors | list[int]
)]


class TypingResultSpatyper(RWModel):
    """Spatyper results"""

    sequence_name: str | None
    repeats: str | None
    type: str | None


class SpatyperTypingMethodIndex(RWModel):
    """Method Index Spatyper."""

    type: Literal[TypingMethod.SPATYPE]
    software: Literal[TypingSoftware.SPATYPER]
    result: TypingResultSpatyper
