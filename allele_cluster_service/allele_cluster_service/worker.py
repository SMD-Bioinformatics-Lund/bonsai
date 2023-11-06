"""Service entrypoint for minhash service."""
import logging
from logging.config import dictConfig

from app import config, tasks
from redis import Redis
from rq import Connection, Queue, Worker

dictConfig(config.DICT_CONFIG)
LOG = logging.getLogger(__name__)


def create_app():
    """Start a new worker instance."""
    LOG.info("Preparing to start worker")
    LOG.info(f"Setup redis connection: {config.REDIS_HOST}:{config.REDIS_PORT}")
    redis = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)

    # start worker with json serializer
    LOG.info("Starting worker...")
    with Connection(redis):
        queue = Queue(config.REDIS_QUEUE)
        worker = Worker([queue], connection=redis)
        worker.work()
