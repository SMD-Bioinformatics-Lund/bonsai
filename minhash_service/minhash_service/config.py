"""Configuration for minhash service"""
from os import getenv

# Sourmash variables
SIGNATURE_KMER_SIZE = int(getenv("KMER_SIZE", 31))
GENOME_SIGNATURE_DIR = getenv("DB_PATH", "/data/signature_db")

# Sourmash variables
REDIS_HOST = getenv("REDIS_HOST", "redis")
REDIS_PORT = getenv("REDIS_PORT", "6379")
REDIS_QUEUE = "minhash"

# Logging configuration
DICT_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "default": {
            "level": "DEBUG",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",  # Default is stderr
        },
    },
    "loggers": {
        "root": {  # root logger
            "handlers": ["default"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
