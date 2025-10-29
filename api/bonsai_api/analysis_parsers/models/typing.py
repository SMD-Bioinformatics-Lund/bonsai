"""Typing related data models"""

from enum import Enum
from typing import Any, Literal, Optional, Union

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
    SCCMEC = "sccmec"


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
    SCCMECTYPE = "sccmectype"


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

    alleles: dict[str, Union[int, str, list, None]]


class TypingResultMlst(ResultMlstBase):
    """MLST results"""

    scheme: str
    sequence_type: Optional[int] = Field(None, alias="sequenceType")


class TypingResultCgMlst(ResultMlstBase):
    """MLST results"""

    n_novel: int = Field(0, alias="nNovel")
    n_missing: int = Field(0, alias="nNovel")


class TypingResultShiga(RWModel):
    """Container for shigatype gene information"""

    rfb: Optional[str] = None
    rfb_hits: Optional[float] = None
    mlst: Optional[str] = None
    flic: Optional[str] = None
    crispr: Optional[str] = None
    ipah: str
    predicted_serotype: str
    predicted_flex_serotype: Optional[str] = None
    comments: Optional[str] = None


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


CgmlstAlleles = dict[str, int | None | ChewbbacaErrors | MlstErrors | list[int]]


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


class TypingResultSccmec(RWModel):
    """Sccmec results"""
    type: str | None = None
    subtype: str | None = None
    mecA: str | None = None
    targets: list[str] | None = None
    regions: list[str] | None = None
    target_schema: str
    target_schema_version: str
    region_schema: str
    region_schema_version: str
    camlhmp_version: str
    coverage: list[float] | None = None
    hits: list[int] | None = None
    target_comment: str | None = None
    region_comment: str | None = None
    comment: str | None = None


class SccmecTypingMethodIndex(RWModel):
    """Method Index Sccmec."""
    type: Literal[TypingMethod.SCCMECTYPE]
    software: Literal[TypingSoftware.SCCMEC]
    result: TypingResultSccmec
