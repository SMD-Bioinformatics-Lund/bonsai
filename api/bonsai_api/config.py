"""Mimer api default configuration"""

import re
import os
import ssl
import tomllib
from typing import Annotated
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError, model_validator, FilePath, AfterValidator
from pydantic_settings import BaseSettings, SettingsConfigDict

ssl_defaults = ssl.get_default_verify_paths()

# read default config and user defined config
config_file = [Path(__file__).parent.joinpath("config.toml")]  # built in config file

CUSTOM_CONFIG_ENV_NAME = "CONFIG_FILE"
custom_config = os.getenv(CUSTOM_CONFIG_ENV_NAME)
if custom_config is not None:
    user_cnf = Path(custom_config)
    if user_cnf.exists():
        config_file.append(user_cnf)


def _validate_yaml_file(path: Path | None) -> Path | None:
    """Ensure that file is readable and looks like a YAML."""
    if path is None:
         return None
    if not os.access(path, os.R_OK):
        raise ValueError(f"LIMS export config file is not readable: {path}")
    if path.suffix.lower() not in {'.yaml', '.yml'}:
        raise ValueError(f"LIMS export config must be a .yaml or .yml file: {path}")
    return path.resolve()


LimsConfigPath = Annotated[
    FilePath | None,
    AfterValidator(_validate_yaml_file)
]


class SmtpConfig(BaseSettings):
    """SMTP server configuration."""

    host: str
    port: int = 25
    timeout: int = Field(60, description="Conection timeout in seconds.")
    use_tls: bool = False
    use_ssl: bool = False


class EmailConfig(BaseSettings):

    subject_prefix: str = "[ Bonsai ]"
    sender: str = 'do-not-reply@bonsai.app'
    sender_name: str = "Bonsai"


class BrackenThresholds(BaseModel):
    model_config = ConfigDict(extra='forbid')
    min_fraction: float = Field(ge=0.0, le=1.0)
    min_reads: int = Field(ge=0)


class MykrobeThresholds(BaseModel):
    model_config = ConfigDict(extra='forbid')
    min_species_coverage: float = Field(ge=0.0, le=1.0)
    min_phylogenetic_group_coverage: float = Field(ge=0.0, le=1.0)


_species_key_pattern = re.compile(r"^[a-z0-9_]+$")

def _validate_species_keys(d: dict[str, object], method_name: str) -> None:
    for key in d.keys():
        if key == "default":
            continue
        if not _species_key_pattern.fullmatch(key):
            raise ValueError(
                f"[species.{method_name}.{key}] is not valid. "
                f"Use lowercase snake_case (a-z0-9_)."
            )

def normalize_species_key(name: str) -> str:
    # Same normalization used by lookup helpers:
    # lower, spaces/hyphens to underscores; strip stray chars
    key = name.strip().lower().replace(" ", "_").replace("-", "_")
    key = re.sub(r"[^a-z0-9_]", "", key)
    return key


class SpeciesCategory(BaseModel):
    model_config = ConfigDict(extra='forbid')
    bracken: dict[str, BrackenThresholds] = Field(default_factory=dict)
    mykrobe: dict[str, MykrobeThresholds] = Field(default_factory=dict)

    @model_validator(mode='after')
    def _validate_species_keys(self) -> "SpeciesCategory":
        _validate_species_keys(self.bracken, "bracken")
        _validate_species_keys(self.mykrobe, "mykrobe")

        # Ensure defaults exist if your code relies on them
        if "default" not in self.bracken:
            raise ValueError("[species.bracken.default] must be defined.")
        if "default" not in self.mykrobe:
            raise ValueError("[species.mykrobe.default] must be defined.")
        return self

    def get_bracken(self, species: str) -> BrackenThresholds:
        key = normalize_species_key(species)
        return self.bracken.get(key) or self.bracken.get("default")

    def get_mykrobe(self, species: str) -> MykrobeThresholds:
        key = normalize_species_key(species)
        return self.mykrobe.get(key) or self.mykrobe.get("default")


class QCConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    species: SpeciesCategory


class Settings(BaseSettings):
    """API configuration."""

    # Configure allowed origins (CORS) for development. Origins are a comma seperated list.
    # https://fastapi.tiangolo.com/tutorial/cors/
    allowed_origins: list[str] = []

    # Database connection
    # standard URI has the form:
    # mongodb://[username:password@]host1[:port1][,...hostN[:portN]][/[defaultauthdb][?options]]
    # read more: https://docs.mongodb.com/manual/reference/connection-string/
    database_name: str = "bonsai"
    db_host: str = "mongodb"
    db_port: int = 27017
    max_connections: int = 10
    min_connections: int = 10

    # Redis connection
    redis_host: str = "redis"
    redis_port: str = "6379"

    # Reference genome and annotations for IGV
    reference_genomes_dir: str = "/tmp/reference_genomes"
    annotations_dir: str = "/tmp/annotations"
    # authentication options
    secret_key: str = "not-so-secret"  # openssl rand -hex 32
    access_token_expire_minutes: int = 180  # expiration time for accesst token
    api_authentication: bool = True

    # notification api for sending emails
    notification_service_api: HttpUrl | None = None
    audit_log_service_api: HttpUrl | None = None

    # LDAP login Settings
    # If LDAP is not configured it will fallback on local authentication
    ldap_search_attr: str = "mail"
    ldap_search_filter: str | None = None
    ldap_base_dn: str | None = None
    # ldap server
    ldap_host: str | None = None
    ldap_port: int = 1389
    ldap_bind_dn: str | None = None
    ldap_secret: str | None = None
    ldap_connection_timeout: int = 10
    ldap_read_only: bool = False
    ldap_valid_names: str | None = None
    ldap_private_key_password: str | None = None
    ldap_raise_exceptions: bool = False
    ldap_user_login_attr: str = "mail"
    force_attribute_value_as_list: bool = False
    # ldap tls
    ldap_use_ssl: bool = False
    ldap_use_tls: bool = True
    ldap_tls_version: int = ssl.PROTOCOL_TLSv1
    ldap_require_cert: int = ssl.CERT_REQUIRED
    ldap_client_private_key: str | None = None
    ldap_client_cert: str | None = None
    # ldap ssl
    ldap_ca_certs_file: str | None = ssl_defaults.cafile
    ldap_ca_certs_path: str | None = ssl_defaults.capath
    ldap_ca_certs_data: str | None = None

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        toml_file=config_file,
    )

    lims_export_config: LimsConfigPath = Field(
        default=None, 
        description=(
            "Path to custom LIMS exporter YAML configuration."
            "If omitted, the application will fall back the packaged default."
        ),
        examples=["/etc/bonsai/lims.yaml"]
        )

    @property
    def use_ldap_auth(self) -> bool:
        """Return True if LDAP authentication is enabled.

        :return: Return True if LDAP authentication is enabled
        :rtype: bool
        """
        return self.ldap_host is not None

    @property
    def mongodb_uri(self) -> str | None:
        """Create mongodb connection string."""

        return f"mongodb://{self.db_host}:{self.db_port}/{self.database_name}"


# to get a string like this run:
# openssl rand -hex 32
ALGORITHM = "HS256"

# Definition of user roles
USER_ROLES = {
    "admin": [
        "users:me",
        "users:read",
        "users:write",
        "groups:read",
        "groups:write",
        "samples:read",
        "samples:write",
        "samples:update",
        "locations:read",
        "locations:write",
    ],
    "user": [
        "users:me",
        "samples:read",
        "samples:update",
        "groups:read",
        "locations:read",
        "locations:write",
    ],
    "uploader": [
        "groups:write" "samples:write",
    ],
}

# load raw thresholds
thresholds_file = Path(__file__).parent.joinpath("thresholds.toml")  # built in config file
with thresholds_file.open('rb') as inpt:
    try:
        thresholds = tomllib.load(inpt)
        thresholds_cfg = QCConfig.model_validate(thresholds)
    except ValidationError as error:
        raise RuntimeError(f"Invalid QC thresholds in {thresholds_file}:\n{error}") from error


settings = Settings()

