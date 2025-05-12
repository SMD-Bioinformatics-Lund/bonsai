"""Contain all constants used by various data modules."""


from enum import StrEnum


class TypingSoftware(StrEnum):
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


class TypingMethod(StrEnum):
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


class ChewbbacaErrors(StrEnum):
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


class MlstErrors(StrEnum):
    """MLST error codes."""

    NOVEL = "novel"
    PARTIAL = "partial"


class QcSoftware(StrEnum):
    """Valid tools."""

    QUAST = "quast"
    FASTQC = "fastqc"
    POSTALIGNQC = "postalignqc"
    CHEWBBACA = TypingSoftware.CHEWBBACA.value
    GAMBITCORE = "gambitcore"

class PredictionSoftware(StrEnum):
    """Container for prediciton software names."""

    AMRFINDER = "amrfinder"
    RESFINDER = "resfinder"
    VIRFINDER = "virulencefinder"
    SEROTYPEFINDER = "serotypefinder"
    MYKROBE = "mykrobe"
    TBPROFILER = "tbprofiler"


class SequenceStand(StrEnum):
    """Definition of DNA strand."""

    FORWARD = "+"
    REVERSE = "-"


class VariantType(StrEnum):
    """Types of variants."""

    SNV = "SNV"
    MNV = "MNV"
    SV = "SV"
    INDEL = "INDEL"
    STR = "STR"


class VariantSubType(StrEnum):
    """Variant subtypes."""

    INSERTION = "INS"
    DELETION = "DEL"
    SUBSTITUTION = "SUB"
    TRANSISTION = "TS"
    TRANSVERTION = "TV"
    INVERSION = "INV"
    DUPLICATION = "DUP"
    TRANSLOCATION = "BND"