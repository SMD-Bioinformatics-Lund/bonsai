"""Service entrypoint for minhash service."""
import logging
from logging.config import dictConfig

from redis import Redis
from rq import Connection, Queue, Worker

from .config import LOG_CONFIG, settings

dictConfig(LOG_CONFIG)
LOG = logging.getLogger(__name__)


def create_app():
    """Start a new worker instance."""
    LOG.info("Preparing to start worker")
    LOG.info("Setup redis connection: %s:%s", settings.redis.host, settings.redis.port)
    redis = Redis(host=settings.redis.host, port=settings.redis.port)

    # start worker with json serializer
    LOG.info("Starting worker...")
    with Connection(redis):
        queue = Queue(settings.redis.queue)
        worker = Worker([queue], connection=redis)
        worker.work()
