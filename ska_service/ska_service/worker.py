"""Service entrypoint for minhash service."""

import logging
from logging.config import dictConfig

from redis import Redis
from rq import Connection, Queue, Worker

from .config import settings

# Logging configuration
DICT_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "default": {
            "level": settings.log_level,
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


# setup logging
dictConfig(DICT_CONFIG)
LOG = logging.getLogger(__name__)


def create_app():
    """Start a new worker instance."""
    LOG.info("Preparing to start worker")
    LOG.info("Setup redis connection: %s:%s", settings.REDIS_HOST, settings.REDIS_PORT)
    redis = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)

    # start worker with json serializer
    LOG.info("Starting worker...")
    with Connection(redis):
        queue = Queue(settings.REDIS_QUEUE)
        worker = Worker([queue], connection=redis)
        worker.work()
