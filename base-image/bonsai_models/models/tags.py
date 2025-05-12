"""Definition of tags."""

from enum import StrEnum

from .base import RWModel


class TagType(StrEnum):
    """Categories of tags."""

    VIRULENCE = "virulence"
    RESISTANCE = "resistane"
    TYPING = "typing"
    QC = "qc"


class ResistanceTag(StrEnum):
    """AMR associated tags."""

    VRE = "VRE"
    ESBL = "ESBL"
    MRSA = "MRSA"
    MSSA = "MSSA"


class VirulenceTag(StrEnum):
    """Virulence associated tags."""

    PVL_ALL_POS = "pos"
    PVL_LUKS_POS = "neg/pos"
    PVL_LUKF_POS = "pos/neg"
    PVL_ALL_NEG = "neg"


class TagSeverity(StrEnum):
    """Defined severity classes of tags"""

    INFO = "info"
    PASSED = "success"
    WARNING = "warning"
    DANGER = "danger"


class Tag(RWModel):
    """Tag data structure."""

    type: TagType
    label: VirulenceTag | ResistanceTag
    description: str
    severity: TagSeverity


TagList = list[Tag]
