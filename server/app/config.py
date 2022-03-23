"""Mimer api default configuration"""
import os

# Database connection
# standard URI has the form:
# mongodb://[username:password@]host1[:port1][,...hostN[:portN]][/[defaultauthdb][?options]]
# read more: https://docs.mongodb.com/manual/reference/connection-string/
DATABASE_NAME = os.getenv("DATABASE_NAME", "mimer")
DB_HOST = os.getenv("DB_HOST", "mongodb")
DB_PORT = os.getenv("DB_PORT", "27017")
MONGODB_URI = f"mongodb://{DB_HOST}:{DB_PORT}/{DATABASE_NAME}"
MAX_CONNECTIONS = int(os.getenv("MAX_CONNECTIONS", 10))
MIN_CONNECTIONS = int(os.getenv("MIN_CONNECTIONS", 10))

# Configure allowed origins (CORS) for development. Origins are a comma seperated list.
# https://fastapi.tiangolo.com/tutorial/cors/
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
