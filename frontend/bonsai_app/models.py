"""Data modules shared by the application."""

from enum import Enum
from typing import Any, List

from pydantic import BaseModel, ConfigDict


class RWModel(BaseModel):  # pylint: disable=too-few-public-methods
    """Base model for read/ write operations"""

    model_config = ConfigDict(
        allow_population_by_alias=True,
        populate_by_name=True,
        use_enum_values=True,
    )


class ApiGetSamplesDetailsInput(BaseModel):
    """Input parameters for getting sample details."""

    limit: int | None = None
    skip: int | None = None
    prediction_result: bool = True
    qc_metrics: bool = False
    sid: list[str] | None = None


class TableColumn(BaseModel):
    """Data structure for a cell in tabular data."""

    id: str
    label: str
    type: str = "string"
    visible: bool = True
    sortable: bool = True
    searchable: bool = True
    renderer: str = "text_renderer"


TableCell = dict[str, Any]


class TableData(BaseModel):
    """Data structure for tabular data."""

    columns: list[TableColumn]
    rows: list[TableCell]


class SampleBasketObject(RWModel):  # pylint: disable=too-few-public-methods
    """Contaner for sample baskt content."""

    sample_id: str
    assay: str


class QualityControlResult(Enum):
    """QC statuses"""

    PASSED = "passed"
    FAILED = "failed"
    UNPROCESSED = "unprocessed"


class BadSampleQualityAction(Enum):
    """Actions that could be taken if a sample have low quality."""

    # phenotype
    REEXTRACTION = "new extraction"
    RESEQUENCE = "resequence"
    FAILED = "permanent fail"


class PredictionSoftware(Enum):
    """Container for software names."""

    # phenotype
    AMRFINDER = "amrfinder"
    RESFINDER = "resfinder"
    VIRFINDER = "virulencefinder"


class ElementType(Enum):
    """Prediction categories."""

    AMR = "AMR"
    ACID = "STRESS_ACID"
    BIOCIDE = "STRESS_BIOCIDE"
    METAL = "STRESS_METAL"
    HEAT = "STRESS_HEAT"
    VIR = "VIRULENCE"


class TagType(Enum):
    """Tag categories."""

    VIRULENCE = "virulence"
    RESISTANCE = "resistane"
    QC = "qc"


class ResistanceTag(Enum):
    """Tags associated with AMR."""

    VRE = "VRE"
    ESBL = "ESBL"
    MRSA = "MRSA"
    MSSA = "MSSA"


class VirulenceTag(Enum):
    """Virulence associated tags."""

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


class Tag(RWModel):  # pylint: disable=too-few-public-methods
    """Tag data structure."""

    type: TagType
    label: VirulenceTag | ResistanceTag
    description: str
    severity: Severity


class PhenotypeType(Enum):
    """Valid phenotyp methods."""

    ANTIMICROBIAL_RESISTANCE = "antimicrobial_resistance"
    CHEMICAL_RESISTANCE = "chemical_resistance"
    ENVIRONMENTAL_RESISTANCE = "environmental_factor_resistance"
    VIRULENCE = "virulence"


class SubmittedJob(RWModel):  # pylint: disable=too-few-public-methods
    """Container for submitted jobs."""

    id: str
    task: str


NT_TO_AA = {
    "TTT": "F",
    "TTC": "F",
    "TTA": "L",
    "TCT": "S",
    "TCC": "S",
    "TCA": "S",
    "TCG": "S",
    "TAT": "Y",
    "TAC": "Y",  # noqa: E241
    "TGT": "C",
    "TGC": "C",
    "TGG": "W",  # noqa: E241
    "CTT": "L",
    "CTC": "L",
    "CTA": "L",
    "CCT": "P",
    "CCC": "P",
    "CCA": "P",
    "CCG": "P",
    "CAT": "H",
    "CAC": "H",
    "CAA": "Q",
    "CAG": "Q",
    "CGT": "R",
    "CGC": "R",
    "CGA": "R",
    "CGG": "R",
    "ACT": "T",
    "ACC": "T",
    "ACA": "T",
    "ACG": "T",
    "AAT": "N",
    "AAC": "N",
    "AAA": "K",
    "AAG": "K",
    "AGT": "S",
    "AGC": "S",
    "AGA": "R",
    "AGG": "R",
    "GTT": "V",
    "GTC": "V",
    "GTA": "V",
    "GCT": "A",
    "GCC": "A",
    "GCA": "A",
    "GCG": "A",
    "GAT": "D",
    "GAC": "D",
    "GAA": "E",
    "GAG": "E",
    "GGT": "G",
    "GGC": "G",
    "GGA": "G",
    "GGG": "G",
    "TAA": "STOP",
    "TAG": "STOP",
    "TGA": "STOP",
    "TTG": "M",
    "CTG": "M",
    "ATT": "M",
    "ATC": "M",
    "ATA": "M",
    "ATG": "M",
    "GTG": "M",
}

TagList = List[Tag]
