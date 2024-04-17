"""Mimer api default configuration"""
from pydantic_settings import BaseSettings
import os
import ssl

# Database connection
# standard URI has the form:
# mongodb://[username:password@]host1[:port1][,...hostN[:portN]][/[defaultauthdb][?options]]
# read more: https://docs.mongodb.com/manual/reference/connection-string/
DATABASE_NAME = os.getenv("DATABASE_NAME", "bonsai")
DB_HOST = os.getenv("DB_HOST", "mongodb")
DB_PORT = os.getenv("DB_PORT", "27017")
MONGODB_URI = f"mongodb://{DB_HOST}:{DB_PORT}/{DATABASE_NAME}"
MAX_CONNECTIONS = int(os.getenv("MAX_CONNECTIONS", "10"))
MIN_CONNECTIONS = int(os.getenv("MIN_CONNECTIONS", "10"))

# Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

# Reference genome and annotations for IGV
REFERENCE_GENOMES_DIR = os.getenv("REFERENCE_GENOMES_DIR", "/tmp/reference_genomes")
ANNOTATIONS_DIR = os.getenv("ANNOTATIONS_DIR", "/tmp/annotations")

# Configure allowed origins (CORS) for development. Origins are a comma seperated list.
# https://fastapi.tiangolo.com/tutorial/cors/
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "not-so-secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 180

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
        "groups:write"
        "samples:write",
    ],
}

# Configure authentication method used
# If LDAP is not configured it will fallback on local authentication

# LDAP login Settings
ssl_defaults = ssl.get_default_verify_paths()
class Settings(BaseSettings):
    # ldap authentication
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
    def use_ldap(self) -> bool:
        return self.ldap_host is not None

settings = Settings()