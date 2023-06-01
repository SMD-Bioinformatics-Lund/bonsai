"""Typing related data models"""

from enum import Enum
from typing import Dict

from pydantic import Field

from .base import RWModel


class TypingSoftware(Enum):
    """Container for software names."""

    CHEWBBACA = "chewbbaca"
    MLST = "mlst"


class ChewbbacaErrors(Enum):
    """Chewbbaca error codes."""

    PLOT5 = "PLOT5"
    PLOT3 = "PLOT3"
    LOTSC = "LOTSC"
    NIPH = "NIPH"
    NIPHEM = "NIPHEM"
    ALM = "ALM"
    ASM = "ASM"
    LNF = "LNF"


CGMLST_ALLELES = Dict[str, int | None | ChewbbacaErrors]


class ResultMlstBase(RWModel):
    """Base class for storing MLST-like typing results"""

    alleles: CGMLST_ALLELES


class TypingResultMlst(ResultMlstBase):
    """MLST results"""

    scheme: str
    sequence_type: int | None = Field(None)


class TypingResultCgMlst(ResultMlstBase):
    """MLST results"""

    n_novel: int = Field(0)
    n_missing: int = Field(0)


class TypingMethod(Enum):
    """Valid typing methods."""

    MLST = "mlst"
    CGMLST = "cgmlst"


class TypingResultIndex(RWModel):
    """Basic key-value index for analysis results."""

    type: TypingMethod
    result: TypingResultMlst | TypingResultCgMlst
