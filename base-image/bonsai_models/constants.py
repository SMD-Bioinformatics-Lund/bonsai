"""Constants used by Bonsai and accessory services."""

from enum import StrEnum


class AntibioticFamily(StrEnum):
    """Antibiotic classes"""

    AMINOCYCLITOL = "aminocyclitol"
    AMINOGLYCOSIDE = "aminoglycoside"
    AMPHENICOL = "amphenicol"
    NITROIMIDAZOLE = "nitroimidazole"
    FLUOROQUINOLONE = "fluoroquinolone"
    FOSFOMYCIN = "fosfomycin"
    IMINOPHENAZINE = "iminophenazine"
    STEROID_ANTIBACTERIAL = "steroid antibacterial"
    POLYMYXIN = "polymyxin"
    DIARYLQUINOLINE = "diarylquinoline"
    RIFAMYCIN = "rifamycin"
    PSEUDOMONIC_ACID = "pseudomonic acid"
    SALICYLIC_ACID_ANTI_FOLATE = "salicylic acid - anti-folate"
    TETRACYCLINE = "tetracycline"
    MACROLIDE = "macrolide"
    LINCOSAMIDE = "lincosamide"
    STREPTOGRAMIN_B = "streptogramin b"
    ISONICOTINIC_ACID = "isonicotinic acid hydrazide"
    IONOPHORES = "ionophores"
    FOLATE_PATHWAY_ANTAGONIST = "folate pathway antagonist"
    THIOAMIDE = "thioamide"
    BETA_LACTAM = "beta-lactam"
    OXAZOLIDINONE = "oxazolidinone"
    STREPTOGRAMIN_A = "streptogramin a"
    GLYCOPEPTIDE = "glycopeptide"
    ANALOG_OF_D_ALANINE = "analog of d-alanine"
    NICOTINAMIDE = "synthetic derivative of nicotinamide"
    QUINOLONE = "quinolone"
    PLEUROMUTILIN = "pleuromutilin"
    UNSPECIFIED = "unspecified"
    DEV = "under_development"


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


class DistanceMethod(StrEnum):
    """Valid distance methods for hierarchical clustering of samples."""

    JACCARD = "jaccard"
    HAMMING = "hamming"


class ClusterMethod(StrEnum):
    """Index of methods for hierarchical clustering of samples."""

    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"
    NJ = "neighbor_joining"


class SampleQcStatus(StrEnum):
    """QC statuses."""

    # phenotype
    PASSED = "passed"
    FAILED = "failed"
    UNPROCESSED = "unprocessed"


class BadSampleQualityAction(StrEnum):
    """Actions that could be taken if a sample have low quality."""

    # phenotype
    REEXTRACTION = "new extraction"
    RESEQUENCE = "resequence"
    FAILED = "permanent fail"


class ResistanceLevel(StrEnum):
    """The level of resistance a gene or variant yeilds."""

    HIGH = "high"
    LOW = "low"


class MetadataTypes(StrEnum):
    """Valid datatypes for metadata records."""

    STR = "string"
    INT = "integer"
    FLOAT = "float"
