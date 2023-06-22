from pydantic import BaseModel, BaseConfig
from enum import Enum
from typing import List


class RWModel(BaseModel):
    """Base model for read/ write operations"""

    class Config(BaseConfig):
        allow_population_by_alias = True
        allow_population_by_field_name = True
        use_enum_values = True


class PredictionSoftware(Enum):
    """Container for software names."""

    # phenotype
    AMRFINDER = "amrfinder"
    RESFINDER = "resfinder"
    VIRFINDER = "virulencefinder"


class ElementType(Enum):
    AMR = "AMR"
    ACID = "STRESS_ACID"
    BIOCIDE = "STRESS_BIOCIDE"
    METAL = "STRESS_METAL"
    HEAT = "STRESS_HEAT"
    VIR = "VIRULENCE"


class TagType(Enum):
    VIRULENCE = "virulence"
    RESISTANCE = "resistane"
    QC = "qc"


class ResistanceTag(Enum):
    VRE = "VRE"
    ESBL = "ESBL"
    MRSA = "MRSA"


class VirulenceTag(Enum):
    PVL_ALL_POS = "pos"
    PVL_LUKS_POS = "neg/pos"
    PVL_LUKF_POS = "pos/neg"
    PVL_ALL_NEG = "neg"


class Severity(Enum):
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
    severity: Severity


TAG_LIST = List[Tag]


class PhenotypeType(Enum):
    """Valid phenotyp methods."""

    ANTIMICROBIAL_RESISTANCE = "antimicrobial_resistance"
    CHEMICAL_RESISTANCE = "chemical_resistance"
    ENVIRONMENTAL_RESISTANCE = "environmental_factor_resistance"
    VIRULENCE = "virulence"
