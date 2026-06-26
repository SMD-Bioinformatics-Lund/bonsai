"""Definition of tags."""

from enum import StrEnum
from typing import List

from .base import RWModel


class TagType(StrEnum):
    """Categories of tags."""

    VIRULENCE = "virulence"
    RESISTANCE = "resistane"
    QC = "qc"
    TYPING = "typing"


class ResistanceTag(StrEnum):
    """AMR associated tags."""

    VRE = "VRE"
    ESBL = "ESBL"
    MRSA = "MRSA"
    MSSA = "MSSA"


class VirulenceTag(StrEnum):
    """Virulence associated tags."""

    PVL_ALL_POS = "PVL pos"
    PVL_LUKS_POS = "LukS Pos"
    PVL_LUKF_POS = "LukF Pos"
    PVL_ALL_NEG = "PVL neg"


class TagSeverity(StrEnum):
    """Defined severity classes of tags"""

    INFO = "info"
    PASSED = "success"
    WARNING = "warning"
    DANGER = "danger"


class Tag(RWModel):
    """Tag data structure."""

    type: TagType
    label: VirulenceTag | ResistanceTag | str
    description: str
    severity: TagSeverity


TagList = List[Tag]
