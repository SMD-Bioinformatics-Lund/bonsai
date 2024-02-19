"""Antibiotic information."""

from enum import Enum
from pydantic import BaseModel


class AntiboiticFamily(Enum):
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
    ISONICOTINIC_ACID_HYDRAZIDE = "isonicotinic acid hydrazide"
    IONOPHORES = "ionophores"
    FOLATE_PATHWAY_ANTAGONIST = "folate pathway antagonist"
    THIOAMIDE = "thioamide"
    BETA_LACTAM = "beta-lactam"
    OXAZOLIDINONE = "oxazolidinone"
    STREPTOGRAMIN_A = "streptogramin a"
    GLYCOPEPTIDE = "glycopeptide"
    ANALOG_OF_D_ALANINE = "analog of d-alanine"
    SYNTHETIC_DERIVATIVE_OF_NICOTINAMIDE = "synthetic derivative of nicotinamide"
    QUINOLONE = "quinolone"
    PLEUROMUTILIN = "pleuromutilin"
    UNSPECIFIED = "unspecified"
    UNDER_DEVELOPMENT = "under_development"


class AntibioticInfo(BaseModel):  # pylint: disable=too-few-public-methods
    """Antibiotic information."""

    name: str
    family: AntiboiticFamily
    abbreviation: str | None = None


ANTIBIOTICS = tuple([
    AntibioticInfo(name='unknown aminocyclitol', family='aminocyclitol'),
    AntibioticInfo(name='spectinomycin', family='aminocyclitol'),
    AntibioticInfo(name='unknown aminoglycoside', family='aminoglycoside'),
    AntibioticInfo(name='gentamicin', family='aminoglycoside'),
    AntibioticInfo(name='gentamicin c', family='aminoglycoside'),
    AntibioticInfo(name='tobramycin', family='aminoglycoside'),
    AntibioticInfo(name='streptomycin', family='aminoglycoside'),
    AntibioticInfo(name='amikacin', family='aminoglycoside'),
    AntibioticInfo(name='kanamycin', family='aminoglycoside'),
    AntibioticInfo(name='kanamycin a', family='aminoglycoside'),
    AntibioticInfo(name='neomycin', family='aminoglycoside'),
    AntibioticInfo(name='paromomycin', family='aminoglycoside'),
    AntibioticInfo(name='kasugamycin', family='aminoglycoside'),
    AntibioticInfo(name='g418', family='aminoglycoside'),
    AntibioticInfo(name='capreomycin', family='aminoglycoside'),
    AntibioticInfo(name='isepamicin', family='aminoglycoside'),
    AntibioticInfo(name='dibekacin', family='aminoglycoside'),
    AntibioticInfo(name='lividomycin', family='aminoglycoside'),
    AntibioticInfo(name='ribostamycin', family='aminoglycoside'),
    AntibioticInfo(name='butiromycin', family='aminoglycoside'),
    AntibioticInfo(name='butirosin', family='aminoglycoside'),
    AntibioticInfo(name='hygromycin', family='aminoglycoside'),
    AntibioticInfo(name='netilmicin', family='aminoglycoside'),
    AntibioticInfo(name='apramycin', family='aminoglycoside'),
    AntibioticInfo(name='sisomicin', family='aminoglycoside'),
    AntibioticInfo(name='arbekacin', family='aminoglycoside'),
    AntibioticInfo(name='astromicin', family='aminoglycoside'),
    AntibioticInfo(name='fortimicin', family='aminoglycoside'),
    AntibioticInfo(name='unknown analog of d-alanine', family='analog of d-alanine'),
    AntibioticInfo(name='d-cycloserine', family='analog of d-alanine'),
    AntibioticInfo(name='unknown beta-lactam', family='beta-lactam'),
    AntibioticInfo(name='amoxicillin', family='beta-lactam'),
    AntibioticInfo(name='amoxicillin+clavulanic acid', family='beta-lactam'),
    AntibioticInfo(name='ampicillin', family='beta-lactam'),
    AntibioticInfo(name='ampicillin+clavulanic acid', family='beta-lactam'),
    AntibioticInfo(name='aztreonam', family='beta-lactam'),
    AntibioticInfo(name='cefazolin', family='beta-lactam'),
    AntibioticInfo(name='cefepime', family='beta-lactam'),
    AntibioticInfo(name='cefixime', family='beta-lactam'),
    AntibioticInfo(name='cefotaxime', family='beta-lactam'),
    AntibioticInfo(name='cefotaxime+clavulanic acid', family='beta-lactam'),
    AntibioticInfo(name='cefoxitin', family='beta-lactam'),
    AntibioticInfo(name='ceftaroline', family='beta-lactam'),
    AntibioticInfo(name='ceftazidime', family='beta-lactam'),
    AntibioticInfo(name='ceftazidime+avibactam', family='beta-lactam'),
    AntibioticInfo(name='ceftriaxone', family='beta-lactam'),
    AntibioticInfo(name='cefuroxime', family='beta-lactam'),
    AntibioticInfo(name='cephalothin', family='beta-lactam'),
    AntibioticInfo(name='ertapenem', family='beta-lactam'),
    AntibioticInfo(name='imipenem', family='beta-lactam'),
    AntibioticInfo(name='meropenem', family='beta-lactam'),
    AntibioticInfo(name='penicillin', family='beta-lactam'),
    AntibioticInfo(name='piperacillin', family='beta-lactam'),
    AntibioticInfo(name='piperacillin+tazobactam', family='beta-lactam'),
    AntibioticInfo(name='temocillin', family='beta-lactam'),
    AntibioticInfo(name='ticarcillin', family='beta-lactam'),
    AntibioticInfo(name='ticarcillin+clavulanic acid', family='beta-lactam'),
    AntibioticInfo(name='cephalotin', family='beta-lactam'),
    AntibioticInfo(name='piperacillin+clavulanic acid', family='beta-lactam'),
    AntibioticInfo(name='unknown diarylquinoline', family='diarylquinoline'),
    AntibioticInfo(name='bedaquiline', family='diarylquinoline'),
    AntibioticInfo(name='unknown quinolone', family='quinolone'),
    AntibioticInfo(name='ciprofloxacin', family='quinolone'),
    AntibioticInfo(name='nalidixic acid', family='quinolone'),
    AntibioticInfo(name='fluoroquinolone', family='quinolone'),
    AntibioticInfo(name='unknown folate pathway antagonist', family='folate pathway antagonist'),
    AntibioticInfo(name='sulfamethoxazole', family='folate pathway antagonist'),
    AntibioticInfo(name='trimethoprim', family='folate pathway antagonist'),
    AntibioticInfo(name='unknown fosfomycin', family='fosfomycin'),
    AntibioticInfo(name='fosfomycin', family='fosfomycin'),
    AntibioticInfo(name='unknown glycopeptide', family='glycopeptide'),
    AntibioticInfo(name='vancomycin', family='glycopeptide'),
    AntibioticInfo(name='teicoplanin', family='glycopeptide'),
    AntibioticInfo(name='bleomycin', family='glycopeptide'),
    AntibioticInfo(name='unknown ionophores', family='ionophores'),
    AntibioticInfo(name='narasin', family='ionophores'),
    AntibioticInfo(name='salinomycin', family='ionophores'),
    AntibioticInfo(name='maduramicin', family='ionophores'),
    AntibioticInfo(name='unknown iminophenazine', family='iminophenazine'),
    AntibioticInfo(name='clofazimine', family='iminophenazine'),
    AntibioticInfo(name='unknown isonicotinic acid hydrazide', family='isonicotinic acid hydrazide'),
    AntibioticInfo(name='isoniazid', family='isonicotinic acid hydrazide'),
    AntibioticInfo(name='unknown lincosamide', family='lincosamide'),
    AntibioticInfo(name='lincomycin', family='lincosamide'),
    AntibioticInfo(name='clindamycin', family='lincosamide'),
    AntibioticInfo(name='unknown macrolide', family='macrolide'),
    AntibioticInfo(name='carbomycin', family='macrolide'),
    AntibioticInfo(name='azithromycin', family='macrolide'),
    AntibioticInfo(name='oleandomycin', family='macrolide'),
    AntibioticInfo(name='spiramycin', family='macrolide'),
    AntibioticInfo(name='tylosin', family='macrolide'),
    AntibioticInfo(name='telithromycin', family='macrolide'),
    AntibioticInfo(name='erythromycin', family='macrolide'),
    AntibioticInfo(name='unknown nitroimidazole', family='nitroimidazole'),
    AntibioticInfo(name='metronidazole', family='nitroimidazole'),
    AntibioticInfo(name='unknown oxazolidinone', family='oxazolidinone'),
    AntibioticInfo(name='linezolid', family='oxazolidinone'),
    AntibioticInfo(name='unknown amphenicol', family='amphenicol'),
    AntibioticInfo(name='chloramphenicol', family='amphenicol'),
    AntibioticInfo(name='florfenicol', family='amphenicol'),
    AntibioticInfo(name='unknown pleuromutilin', family='pleuromutilin'),
    AntibioticInfo(name='tiamulin', family='pleuromutilin'),
    AntibioticInfo(name='unknown polymyxin', family='polymyxin'),
    AntibioticInfo(name='colistin', family='polymyxin'),
    AntibioticInfo(name='unknown pseudomonic acid', family='pseudomonic acid'),
    AntibioticInfo(name='mupirocin', family='pseudomonic acid'),
    AntibioticInfo(name='unknown rifamycin', family='rifamycin'),
    AntibioticInfo(name='rifampicin', family=AntiboiticFamily.RIFAMYCIN),
    AntibioticInfo(name='unknown salicylic acid - anti-folate', family='salicylic acid - anti-folate'),
    AntibioticInfo(name='para-aminosalicyclic acid', family='salicylic acid - anti-folate'),
    AntibioticInfo(name='unknown steroid antibacterial', family='steroid antibacterial'),
    AntibioticInfo(name='fusidic acid', family='steroid antibacterial'),
    AntibioticInfo(name='unknown streptogramin a', family='streptogramin a'),
    AntibioticInfo(name='dalfopristin', family='streptogramin a'),
    AntibioticInfo(name='pristinamycin iia', family='streptogramin a'),
    AntibioticInfo(name='virginiamycin m', family='streptogramin a'),
    AntibioticInfo(name='quinupristin+dalfopristin', family='streptogramin a'),
    AntibioticInfo(name='unknown streptogramin b', family='streptogramin b'),
    AntibioticInfo(name='quinupristin', family='streptogramin b'),
    AntibioticInfo(name='pristinamycin ia', family='streptogramin b'),
    AntibioticInfo(name='virginiamycin s', family='streptogramin b'),
    AntibioticInfo(name='unknown synthetic derivative of nicotinamide', family='synthetic derivative of nicotinamide'),
    AntibioticInfo(name='pyrazinamide', family='synthetic derivative of nicotinamide'),
    AntibioticInfo(name='unknown tetracycline', family='tetracycline'),
    AntibioticInfo(name='tetracycline', family='tetracycline'),
    AntibioticInfo(name='doxycycline', family='tetracycline'),
    AntibioticInfo(name='minocycline', family='tetracycline'),
    AntibioticInfo(name='tigecycline', family='tetracycline'),
    AntibioticInfo(name='unknown thioamide', family='thioamide'),
    AntibioticInfo(name='ethionamide', family='thioamide'),
    AntibioticInfo(name='unknown unspecified', family='unspecified'),
    AntibioticInfo(name='ethambutol', family='unspecified'),
    AntibioticInfo(name='cephalosporins', family='under_development'),
    AntibioticInfo(name='carbapenem', family='under_development'),
    AntibioticInfo(name='norfloxacin', family='under_development'),
    AntibioticInfo(name='ceftiofur', family='under_development'),
    AntibioticInfo(name='levofloxacin', family=AntiboiticFamily.QUINOLONE),
    AntibioticInfo(name='moxifloxacin', family=AntiboiticFamily.FLUOROQUINOLONE),
    AntibioticInfo(name='delamanid', family=AntiboiticFamily.NITROIMIDAZOLE),
])