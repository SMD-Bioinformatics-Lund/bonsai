"""Service entrypoint for minhash service."""

import logging
from logging.config import dictConfig

from pymongo import MongoClient
from redis import Redis
from rq import Connection, Queue, SimpleWorker

from . import tasks
from .audit import AuditTrailStore
from .config import LOG_CONFIG, settings
from .infrastructure.signature_repository import SignatureRepository

dictConfig(LOG_CONFIG)
LOG = logging.getLogger(__name__)


def create_app():
    """Start a new worker instance."""
    LOG.info("Preparing to start worker")
    LOG.info("Setup redis connection: %s:%s", settings.redis.host, settings.redis.port)
    redis = Redis(host=settings.redis.host, port=settings.redis.port)

    # Create mongo connection at startup
    client = MongoClient(
        host=settings.mongodb.host,
        port=settings.mongodb.port,
        serverSelectionTimeoutMS=5000,
    )
    sig_store = SignatureRepository(
        client[settings.mongodb.database].get_collection("signatures")
    )
    sig_store.ensure_indexes()
    tasks.inject_store(sig_store)

    at_store = AuditTrailStore(
        client[settings.mongodb.database].get_collection("signatures")
    )
    tasks.inject_store(at_store)

    # start worker with json serializer
    LOG.info("Starting worker...")
    with Connection(redis):
        queue = Queue(settings.redis.queue)
        worker = SimpleWorker([queue], connection=redis)
        worker.work()
