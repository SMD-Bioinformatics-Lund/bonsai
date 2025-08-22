"""Service entrypoint for minhash service."""
import logging
from logging.config import dictConfig

from redis import Redis
from rq import Connection, Queue, SimpleWorker
from pymongo import MongoClient

from . import tasks
from .config import LOG_CONFIG, settings
from .store import SignatureStore


dictConfig(LOG_CONFIG)
LOG = logging.getLogger(__name__)


def create_app():
    """Start a new worker instance."""
    LOG.info("Preparing to start worker")
    LOG.info("Setup redis connection: %s:%s", settings.redis.host, settings.redis.port)
    redis = Redis(host=settings.redis.host, port=settings.redis.port)

    # Create mongo connection at startup
    client = MongoClient(
        host=settings.mongodb.host, port=settings.mongodb.port, serverSelectionTimeoutMS=5000
    )
    store = SignatureStore(client[settings.mongodb.database].get_collection("signatures"))
    store.ensure_indexes()
    tasks.inject_store(store)

    # start worker with json serializer
    LOG.info("Starting worker...")
    with Connection(redis):
        queue = Queue(settings.redis.queue)
        worker = SimpleWorker([queue], connection=redis)
        worker.work()
