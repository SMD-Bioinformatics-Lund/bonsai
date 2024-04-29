"""Mimer api default configuration"""
import ssl
from typing import List

from pydantic_settings import BaseSettings

ssl_defaults = ssl.get_default_verify_paths()


class Settings(BaseSettings):
    """API configuration."""
    # Configure allowed origins (CORS) for development. Origins are a comma seperated list.
    # https://fastapi.tiangolo.com/tutorial/cors/
    allowed_origins: List[str] = []

    # Database connection
    # standard URI has the form:
    # mongodb://[username:password@]host1[:port1][,...hostN[:portN]][/[defaultauthdb][?options]]
    # read more: https://docs.mongodb.com/manual/reference/connection-string/
    database_name: str = "bonsai"
    db_host: str = "mongodb"
    db_port: str = "27017"
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

    @property
    def use_ldap_auth(self) -> bool:
        """Return True if LDAP authentication is enabled.

        :return: Return True if LDAP authentication is enabled
        :rtype: bool
        """
        return self.ldap_host is not None

    @property
    def mongodb_uri(self) -> str | None:
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

settings = Settings()
