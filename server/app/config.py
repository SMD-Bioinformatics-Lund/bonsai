"""Mimer api default configuration"""
# Database connection
# standard URI has the form:
# mongodb://[username:password@]host1[:port1][,...hostN[:portN]][/[defaultauthdb][?options]]
# read more: https://docs.mongodb.com/manual/reference/connection-string/
DATABASE_NAME = "mimer"
MONGODB_URI = f"mongodb://mongodb/{DATABASE_NAME}"
MAX_CONNECTIONS = 10
MIN_CONNECTIONS = 10
