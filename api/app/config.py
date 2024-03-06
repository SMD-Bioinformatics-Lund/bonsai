"""Mimer api default configuration"""
import os

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
    "uploader": ["groups:write"],
}

# Configure authentication method used
# If LDAP is not configured it will fallback on local authentication

# LDAP login Settings
# LDAP_HOST = "localhost"
# LDAP_PORT = 389
# LDAP_BASE_DN = 'cn=admin,dc=example,dc=com
# LDAP_USER_LOGIN_ATTR = "mail"
# LDAP_USE_SSL = False
# LDAP_USE_TLS = True
