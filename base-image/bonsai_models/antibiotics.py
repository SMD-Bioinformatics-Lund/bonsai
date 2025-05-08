"""Antibiotic information."""

from enum import StrEnum
from typing import Sequence

from pydantic import BaseModel


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


class AntibioticInfo(BaseModel):  # pylint: disable=too-few-public-methods
    """Antibiotic information."""

    name: str
    family: AntibioticFamily
    abbreviation: str | None = None


ANTIBIOTICS: Sequence[AntibioticInfo] = [
    AntibioticInfo(name="unknown aminocyclitol", family=AntibioticFamily.AMINOCYCLITOL),
    AntibioticInfo(name="spectinomycin", family=AntibioticFamily.AMINOCYCLITOL),
    AntibioticInfo(name="unknown aminoglycoside", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="gentamicin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="gentamicin c", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="tobramycin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="streptomycin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="amikacin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="kanamycin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="kanamycin a", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="neomycin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="paromomycin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="kasugamycin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="g418", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="capreomycin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="isepamicin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="dibekacin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="lividomycin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="ribostamycin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="butiromycin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="butirosin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="hygromycin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="netilmicin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="apramycin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="sisomicin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="arbekacin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="astromicin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(name="fortimicin", family=AntibioticFamily.AMINOGLYCOSIDE),
    AntibioticInfo(
        name="unknown analog of d-alanine", family=AntibioticFamily.ANALOG_OF_D_ALANINE),
    AntibioticInfo(name="d-cycloserine", family=AntibioticFamily.ANALOG_OF_D_ALANINE),
    AntibioticInfo(name="unknown beta-lactam", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="amoxicillin", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="amoxicillin+clavulanic acid", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="ampicillin", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="ampicillin+clavulanic acid", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="aztreonam", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="cefazolin", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="cefepime", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="cefixime", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="cefotaxime", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="cefotaxime+clavulanic acid", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="cefoxitin", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="ceftaroline", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="ceftazidime", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="ceftazidime+avibactam", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="ceftriaxone", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="cefuroxime", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="cephalothin", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="ertapenem", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="imipenem", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="meropenem", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="penicillin", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="piperacillin", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="piperacillin+tazobactam", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="temocillin", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="ticarcillin", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="ticarcillin+clavulanic acid", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="cephalotin", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="piperacillin+clavulanic acid", family=AntibioticFamily.BETA_LACTAM),
    AntibioticInfo(name="unknown diarylquinoline", family=AntibioticFamily.DIARYLQUINOLINE),
    AntibioticInfo(name="bedaquiline", family=AntibioticFamily.DIARYLQUINOLINE),
    AntibioticInfo(name="unknown quinolone", family=AntibioticFamily.QUINOLONE),
    AntibioticInfo(name="ciprofloxacin", family=AntibioticFamily.QUINOLONE),
    AntibioticInfo(name="nalidixic acid", family=AntibioticFamily.QUINOLONE),
    AntibioticInfo(name="fluoroquinolone", family=AntibioticFamily.QUINOLONE),
    AntibioticInfo(
        name="unknown folate pathway antagonist", family=AntibioticFamily.FOLATE_PATHWAY_ANTAGONIST
    ),
    AntibioticInfo(name="sulfamethoxazole", family=AntibioticFamily.FOLATE_PATHWAY_ANTAGONIST),
    AntibioticInfo(name="trimethoprim", family=AntibioticFamily.FOLATE_PATHWAY_ANTAGONIST),
    AntibioticInfo(name="unknown fosfomycin", family=AntibioticFamily.FOSFOMYCIN),
    AntibioticInfo(name="fosfomycin", family=AntibioticFamily.FOSFOMYCIN),
    AntibioticInfo(name="unknown glycopeptide", family=AntibioticFamily.GLYCOPEPTIDE),
    AntibioticInfo(name="vancomycin", family=AntibioticFamily.GLYCOPEPTIDE),
    AntibioticInfo(name="teicoplanin", family=AntibioticFamily.GLYCOPEPTIDE),
    AntibioticInfo(name="bleomycin", family=AntibioticFamily.GLYCOPEPTIDE),
    AntibioticInfo(name="unknown ionophores", family=AntibioticFamily.IONOPHORES),
    AntibioticInfo(name="narasin", family=AntibioticFamily.IONOPHORES),
    AntibioticInfo(name="salinomycin", family=AntibioticFamily.IONOPHORES),
    AntibioticInfo(name="maduramicin", family=AntibioticFamily.IONOPHORES),
    AntibioticInfo(name="unknown iminophenazine", family=AntibioticFamily.IMINOPHENAZINE),
    AntibioticInfo(name="clofazimine", family=AntibioticFamily.IMINOPHENAZINE),
    AntibioticInfo(
        name="unknown isonicotinic acid hydrazide",
        family=AntibioticFamily.ISONICOTINIC_ACID,
    ),
    AntibioticInfo(name="isoniazid", family=AntibioticFamily.ISONICOTINIC_ACID),
    AntibioticInfo(name="unknown lincosamide", family=AntibioticFamily.LINCOSAMIDE),
    AntibioticInfo(name="lincomycin", family=AntibioticFamily.LINCOSAMIDE),
    AntibioticInfo(name="clindamycin", family=AntibioticFamily.LINCOSAMIDE),
    AntibioticInfo(name="unknown macrolide", family=AntibioticFamily.MACROLIDE),
    AntibioticInfo(name="carbomycin", family=AntibioticFamily.MACROLIDE),
    AntibioticInfo(name="azithromycin", family=AntibioticFamily.MACROLIDE),
    AntibioticInfo(name="oleandomycin", family=AntibioticFamily.MACROLIDE),
    AntibioticInfo(name="spiramycin", family=AntibioticFamily.MACROLIDE),
    AntibioticInfo(name="tylosin", family=AntibioticFamily.MACROLIDE),
    AntibioticInfo(name="telithromycin", family=AntibioticFamily.MACROLIDE),
    AntibioticInfo(name="erythromycin", family=AntibioticFamily.MACROLIDE),
    AntibioticInfo(name="unknown nitroimidazole", family=AntibioticFamily.NITROIMIDAZOLE),
    AntibioticInfo(name="metronidazole", family=AntibioticFamily.NITROIMIDAZOLE),
    AntibioticInfo(name="unknown oxazolidinone", family=AntibioticFamily.OXAZOLIDINONE),
    AntibioticInfo(name="linezolid", family=AntibioticFamily.OXAZOLIDINONE),
    AntibioticInfo(name="unknown amphenicol", family=AntibioticFamily.AMPHENICOL),
    AntibioticInfo(name="chloramphenicol", family=AntibioticFamily.AMPHENICOL),
    AntibioticInfo(name="florfenicol", family=AntibioticFamily.AMPHENICOL),
    AntibioticInfo(name="unknown pleuromutilin", family=AntibioticFamily.PLEUROMUTILIN),
    AntibioticInfo(name="tiamulin", family=AntibioticFamily.PLEUROMUTILIN),
    AntibioticInfo(name="unknown polymyxin", family=AntibioticFamily.POLYMYXIN),
    AntibioticInfo(name="colistin", family=AntibioticFamily.POLYMYXIN),
    AntibioticInfo(name="unknown pseudomonic acid", family=AntibioticFamily.PSEUDOMONIC_ACID),
    AntibioticInfo(name="mupirocin", family=AntibioticFamily.PSEUDOMONIC_ACID),
    AntibioticInfo(name="unknown rifamycin", family=AntibioticFamily.RIFAMYCIN),
    AntibioticInfo(name="rifampicin", family=AntibioticFamily.RIFAMYCIN),
    AntibioticInfo(
        name="unknown salicylic acid - anti-folate",
        family=AntibioticFamily.SALICYLIC_ACID_ANTI_FOLATE,
    ),
    AntibioticInfo(
        name="para-aminosalicyclic acid", family=AntibioticFamily.SALICYLIC_ACID_ANTI_FOLATE
    ),
    AntibioticInfo(
        name="unknown steroid antibacterial", family=AntibioticFamily.STEROID_ANTIBACTERIAL
    ),
    AntibioticInfo(name="fusidic acid", family=AntibioticFamily.STEROID_ANTIBACTERIAL),
    AntibioticInfo(name="unknown streptogramin a", family=AntibioticFamily.STREPTOGRAMIN_A),
    AntibioticInfo(name="dalfopristin", family=AntibioticFamily.STREPTOGRAMIN_A),
    AntibioticInfo(name="pristinamycin iia", family=AntibioticFamily.STREPTOGRAMIN_A),
    AntibioticInfo(name="virginiamycin m", family=AntibioticFamily.STREPTOGRAMIN_A),
    AntibioticInfo(name="quinupristin+dalfopristin", family=AntibioticFamily.STREPTOGRAMIN_A),
    AntibioticInfo(name="unknown streptogramin b", family=AntibioticFamily.STREPTOGRAMIN_B),
    AntibioticInfo(name="quinupristin", family=AntibioticFamily.STREPTOGRAMIN_B),
    AntibioticInfo(name="pristinamycin ia", family=AntibioticFamily.STREPTOGRAMIN_B),
    AntibioticInfo(name="virginiamycin s", family=AntibioticFamily.STREPTOGRAMIN_B),
    AntibioticInfo(
        name="unknown synthetic derivative of nicotinamide",
        family=AntibioticFamily.NICOTINAMIDE,
    ),
    AntibioticInfo(
        name="pyrazinamide", family=AntibioticFamily.NICOTINAMIDE
    ),
    AntibioticInfo(name="unknown tetracycline", family=AntibioticFamily.TETRACYCLINE),
    AntibioticInfo(name="tetracycline", family=AntibioticFamily.TETRACYCLINE),
    AntibioticInfo(name="doxycycline", family=AntibioticFamily.TETRACYCLINE),
    AntibioticInfo(name="minocycline", family=AntibioticFamily.TETRACYCLINE),
    AntibioticInfo(name="tigecycline", family=AntibioticFamily.TETRACYCLINE),
    AntibioticInfo(name="unknown thioamide", family=AntibioticFamily.THIOAMIDE),
    AntibioticInfo(name="ethionamide", family=AntibioticFamily.THIOAMIDE),
    AntibioticInfo(name="unknown unspecified", family=AntibioticFamily.UNSPECIFIED),
    AntibioticInfo(name="ethambutol", family=AntibioticFamily.UNSPECIFIED),
    AntibioticInfo(name="cephalosporins", family=AntibioticFamily.DEV),
    AntibioticInfo(name="carbapenem", family=AntibioticFamily.DEV),
    AntibioticInfo(name="norfloxacin", family=AntibioticFamily.DEV),
    AntibioticInfo(name="ceftiofur", family=AntibioticFamily.DEV),
    AntibioticInfo(name="levofloxacin", family=AntibioticFamily.QUINOLONE),
    AntibioticInfo(name="moxifloxacin", family=AntibioticFamily.FLUOROQUINOLONE),
    AntibioticInfo(name="delamanid", family=AntibioticFamily.NITROIMIDAZOLE),
]

