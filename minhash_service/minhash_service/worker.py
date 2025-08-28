"""Service entrypoint for minhash service."""

import logging

from redis import Redis
from rq import Queue, SimpleWorker
from rq.cron import CronScheduler

from . import tasks
from .config import settings, configure_logging
from .db import MongoDB
from .factories import initialize_indexes

def create_minhash_worker() -> SimpleWorker:
    """Start a new minhash worker instance."""
    configure_logging(settings)
    log = logging.getLogger(__name__)
    log.info("Setup redis connection: %s:%s", settings.redis.host, settings.redis.port)
    redis = Redis(host=settings.redis.host, port=settings.redis.port)

    # Create mongo connection at startup
    log.info("Setup mongodb connection: %s:%s", settings.mongodb.host, settings.mongodb.port)
    MongoDB.setup(host=settings.mongodb.host, port=settings.mongodb.port, db_name=settings.mongodb.database)
    initialize_indexes()

    queue = Queue(settings.redis.queue, connection=redis)
    worker = SimpleWorker([queue], connection=redis)
    return worker

def create_cron_worker() -> CronScheduler:
    """Start a new cron worker instance."""
    configure_logging(settings)
    log = logging.getLogger(__name__)
    log.info("Setup redis connection: %s:%s", settings.redis.host, settings.redis.port)

    redis = Redis(host=settings.redis.host, port=settings.redis.port)
    cron = CronScheduler(connection=redis, logging_level=settings.log_level)

    # setup periodic tasks
    if settings.periodic_integrity_check.endabled:
        cron_string = settings.periodic_integrity_check.cron
        cron.register(tasks.run_data_integrity_check,
                      queue_name=settings.periodic_integrity_check.queue,
                      cron=cron_string)
        log.info("Scheduling periodic integrity check: %s", cron_string)

    if settings.cleanup_removed_files.endabled:
        cron_string = settings.cleanup_removed_files.cron
        cron.register(tasks.cleanup_removed_files,
                      queue_name=settings.cleanup_removed_files.queue,
                      cron=cron_string)
        log.info("Scheduling cleanup of removed files: %s", cron_string)

    return cron