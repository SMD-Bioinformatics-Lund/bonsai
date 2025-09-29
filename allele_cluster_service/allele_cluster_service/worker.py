"""Service entrypoint for minhash service."""

import logging
from logging.config import dictConfig

from redis import Redis
from rq import Queue, Worker

from . import config

dictConfig(config.DICT_CONFIG)
LOG = logging.getLogger(__name__)


def create_app():
    """Start a new worker instance."""
    LOG.info("Preparing to start worker")
    LOG.info("Setup redis connection: %s:%s", config.REDIS_HOST, config.REDIS_PORT)

    redis = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)

    # start worker with json serializer
    LOG.info("Starting worker...")
    queue = Queue(config.REDIS_QUEUE, connection=redis)
    worker = Worker([queue], connection=redis)
    worker.work()
