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
            "level": settings.log_level.upper(),
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",  # Default is stderr
        },
    },
    "loggers": {
        "root": {  # root logger
            "handlers": ["default"],
            "level": settings.log_level.upper(),
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
    LOG.info("Setup redis connection: %s:%s", settings.redis_host, settings.redis_port)
    redis = Redis(host=settings.redis_host, port=settings.redis_port)

    # start worker with json serializer
    LOG.info("Starting worker...")
    with Connection(redis):
        queue = Queue(settings.redis_queue)
        worker = Worker([queue], connection=redis)
        worker.work()
