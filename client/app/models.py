from pydantic import BaseModel, BaseConfig
from enum import Enum
from typing import List


class RWModel(BaseModel):
    """Base model for read/ write operations"""

    class Config(BaseConfig):
        allow_population_by_alias = True
        populate_by_name = True
        use_enum_values = True


class SampleBasketObject(RWModel):
    """Contaner for sample baskt content."""
    sample_id: str
    analysis_profile: str


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


NT_TO_AA = {
        "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
        "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
        "TAT": "Y", "TAC": "Y",                           # noqa: E241
        "TGT": "C", "TGC": "C",             "TGG": "W",   # noqa: E241
        "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
        "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
        "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
        "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
        "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
        "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
        "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
        "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
        "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
        "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
        "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
        "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
        "TAA": "STOP", "TAG": "STOP", "TGA": "STOP",
        "TTG": "M", "CTG": "M", "ATT": "M", "ATC": "M",
        "ATA": "M", "ATG": "M", "GTG": "M",
}