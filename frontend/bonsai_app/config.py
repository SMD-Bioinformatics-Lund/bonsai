"""Configuration of web site"""

import pathlib
from enum import Enum

from pydantic import Field
from pydantic_extra_types.timezone_name import TimeZoneName
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClusterMethod(Enum):  # pylint: disable=too-few-public-methods
    """Index of methods for hierarchical clustering of samples."""

    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"
    NJ = "neighbor_joining"


class TypingMethod(str, Enum):  # pylint: disable=too-few-public-methods
    """Supported typing methods."""

    MLST = "mlst"
    CGMLST = "cgmlst"
    MINHASH = "minhash"


class Settings(BaseSettings):
    """Bonsai frontend configuration."""

    api_internal_url: str = Field("http://api:8000", description="Internal container-container URL to the Bonsai API.")
    api_external_url: str = Field("http://localhost:8001", description="External URL to the Bonsai API.")

    tz: TimeZoneName = Field("Etc/UTC", alias="timezone")

    # verify SSL certificated for https connections to API
    verify_ssl: bool | pathlib.Path = Field(
        True,
        description="If SSL should be verifed for HTTPS requests to the API. Can also provide a path to the CA bundle that should be used.",
    )
    request_timeout: int = Field(
        60, description="Timeout for requests to API in seconds."
    )
    # Session secret key
    secret_key: bytes = Field(
        b"not-so-secret", description="Secret key for encrypting session."
    )

    # parameters for finding similar samples
    sample_view_similarity_limit: int = Field(
        10, description="Limit number of samples in sample view dendrogram."
    )
    sample_view_similarity_threshold: float = Field(
        0.9,
        description="Minimum similarity score for samples in the samples view dendrogram.",
    )
    sample_view_typing_method: TypingMethod = Field(
        TypingMethod.MINHASH,
        description="Typing method used for clustering samples in sample view dendrogram.",
    )
    sample_view_cluster_method: ClusterMethod = Field(
        ClusterMethod.SINGLE,
        description="Clustering method used for dendrogram in sample view.",
    )
    testing: bool = Field(
        False,
        description="Enable test mode to facilitate easier testing and development.",
    )

    model_config = SettingsConfigDict(use_enum_values=True)


settings = Settings()

# res classes
AMR_CLASS = {}

# Antibiotic classes
ANTIBIOTIC_CLASSES = {
    "Aminoglycosides": [
        "Amikacin",
        "Arbekacin",
        "Dibekacin",
        "Gentamicin",
        "Isepamicin",
        "Kanamycin",
        "Micronomicin",
        "Neomycin",
        "Netilmicin",
        "Plazomicin",
        "Ribostamycin",
        "Sisomicin",
        "Streptomycin",
        "Tobramycin",
    ],
    "Penicillins": [
        "Amoxicillin",
        "Ampicillin",
        "Azlocillin",
        "Bacampicillin",
        "Benzathine benzylpenicillin",
        "Benzylpenicillin",
        "Clometocillin",
        "Cloxacillin",
        "Dicloxacillin",
        "Flucloxacillin",
        "Mecillinam",
        "Mezlocillin",
        "Nafcillin",
        "Oxacillin",
        "Penamecillin",
        "Pheneticillin",
        "Phenoxymethylpenicillin",
        "Piperacillin",
        "Pivampicillin",
        "Pivmecillinam",
        "Procaine benzylpenicillin",
        "Sulbenicillin",
    ],
    "Beta-lactam + inhibitor": [
        "Amoxicillin+clavulanic Acid",
        "Ampicillin/sulbactam",
        "Sultamicillin",
        "Piperacillin+tazobactam",
    ],
    "Macrolides": [
        "Azithromycin",
        "Clarithromycin",
        "Dirithromycin",
        "Erythromycin",
        "Josamycin",
        "Lincomycin",
        "Midecamycin",
        "Oleandomycin",
        "Roxithromycin",
        "Spiramycin",
        "Telithromycin",
    ],
    "Monobactams": ["Aztreonam"],
    "Carbapenems": [
        "Biapenem",
        "Doripenem",
        "Ertapenem",
        "Imipenem",
        "Imipenem/cilastatin",
        "Meropenem",
        "Meropenem-vaborbactam",
        "Panipenem",
        "Tebipenem",
    ],
    "Carboxypenicillins": ["Carbenicillin", "Temocillin", "Ticarcillin"],
    "Cephalosporins": [
        "Cefcapene pivoxil",
        "Cefdinir",
        "Cefditoren pivoxil",
        "Cefetamet pivoxil",
        "Cefixime",
        "Cefmenoxime",
        "Cefodizime",
        "Cefoperazone",
        "Cefotaxime",
        "Cefpiramide",
        "Cefpodoxime proxetil",
        "Ceftazidime",
        "Ceftazidime-avibactam",
        "Cefteram pivoxil",
        "Ceftibuten",
        "Ceftizoxime",
        "Ceftriaxone",
        "Latamoxef",
        "Cefaclor",
        "Cefamandole",
        "Cefbuperazone",
        "Cefmetazole",
        "Cefminox",
        "Cefonicid",
        "Ceforanide",
        "Cefotetan",
        "Cefotiam",
        "Cefotiam hexetil",
        "Cefoxitin",
        "Cefprozil",
        "Cefuroxime",
        "Flomoxef",
        "Cefacetrile",
        "Cefadroxil",
        "Cefalexin",
        "Cefalotin",
        "Cefapirin",
        "Cefatrizine",
        "Cefazedone",
        "Cefazolin",
        "Cefradine",
        "Cefroxadine",
        "Ceftezole",
        "Cefepime",
        "Cefoselis",
        "Cefozopran",
        "Cefpirome",
        "Ceftaroline fosamil",
        "Ceftobiprole medocaril",
        "Ceftolozane-tazobactam",
    ],
    "Amphenicols": ["Chloramphenicol", "Thiamphenicol"],
    "Tetracyclines": [
        "Chlortetracycline",
        "Doxycycline",
        "Eravacycline",
        "Lymecycline",
        "Metacycline",
        "Minocycline (IV)",
        "Minocycline (oral)",
        "Omadacycline",
        "Oxytetracycline",
        "Tetracycline",
    ],
    "Fluoroquinolones": [
        "Ciprofloxacin",
        "Delafloxacin",
        "Enoxacin",
        "Fleroxacin",
        "Flumequine",
        "Garenoxacin",
        "Gatifloxacin",
        "Gemifloxacin",
        "Levofloxacin",
        "Lomefloxacin",
        "Moxifloxacin",
        "Norfloxacin",
        "Ofloxacin",
        "Pazufloxacin",
        "Pefloxacin",
        "Prulifloxacin",
        "Rufloxacin",
        "Sitafloxacin",
        "Sparfloxacin",
        "Tosufloxacin",
    ],
    "Lincosamides": ["Clindamycin"],
    "Phenol derivatives": ["Clofoctol"],
    "Polymyxins": ["Colistin", "Polymyxin B"],
    "Glycopeptides": [
        "Dalbavancin",
        "Oritavancin",
        "Teicoplanin",
        "Telavancin",
        "Vancomycin (IV)",
        "Vancomycin (oral)",
    ],
    "Streptogramins": ["Dalfopristin-quinupristin", "Pristinamycin"],
    "Lipopeptides": ["Daptomycin"],
    "Penems": ["Faropenem"],
    "Phosphonics": ["Fosfomycin (IV)", "Fosfomycin (oral)"],
    "Steroid antibacterials": ["Fusidic Acid"],
    "Oxazolidinones": ["Linezolid", "Tedizolid"],
    "Imidazoles": ["Metronidazole (IV)", "Metronidazole (oral)"],
    "Nitrofurantoin": ["Nitrofurantoin"],
    "Rifamycins": ["Rifabutin", "Rifampicin", "Rifamycin", "Rifaximin"],
    "Aminocyclitols": ["Spectinomycin"],
    "Combination of antibiotics": ["Spiramycin/metronidazole"],
    "Trimethoprim - sulfonamide combinations": [
        "Sulfadiazine/trimethoprim",
        "Sulfamethizole/trimethoprim",
        "Sulfamethoxazole/trimethoprim",
        "Sulfametrole/trimethoprim",
        "Sulfamoxole/trimethoprim",
    ],
    "Glycylcyclines": ["Tigecycline"],
    "Trimethoprim": ["Trimethoprim"],
}
