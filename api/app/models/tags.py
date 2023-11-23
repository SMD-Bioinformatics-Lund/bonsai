"""Definition of tag information."""

from enum import Enum
from typing import List

from .base import RWModel


class TagType(Enum):  # pylint: disable=too-few-public-methods
    """Tag categories."""

    VIRULENCE = "virulence"
    RESISTANCE = "resistane"
    QC = "qc"


class ResistanceTag(Enum):  # pylint: disable=too-few-public-methods
    """Tags associated with AMR."""

    VRE = "VRE"
    ESBL = "ESBL"
    MRSA = "MRSA"
    MSSA = "MSSA"


class VirulenceTag(Enum):  # pylint: disable=too-few-public-methods
    """Virulence associated tags."""

    PVL_ALL_POS = "PVL pos"
    PVL_LUKS_POS = "PVL neg/pos"
    PVL_LUKF_POS = "PVL pos/neg"
    PVL_ALL_NEG = "PVL neg"


class TagSeverity(Enum):  # pylint: disable=too-few-public-methods
    """Defined severity classes of tags"""

    INFO = "info"
    PASSED = "success"
    WARNING = "warning"
    DANGER = "danger"


class Tag(RWModel):  # pylint: disable=too-few-public-methods
    """Tag data structure."""

    type: TagType
    label: VirulenceTag | ResistanceTag
    description: str
    severity: TagSeverity


TagList = List[Tag]
