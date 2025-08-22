"""Service entrypoint for minhash service."""

import logging

from redis import Redis
from rq import Queue, SimpleWorker
from rq.cron import CronScheduler

from . import tasks
from .config import cnf, configure_logging
from .db import MongoDB
from .factories import initialize_indexes

def create_minhash_worker() -> SimpleWorker:
    """Start a new minhash worker instance."""
    configure_logging(cnf)
    log = logging.getLogger(__name__)
    log.info("Setup redis connection: %s:%s", cnf.redis.host, cnf.redis.port)
    redis = Redis(host=cnf.redis.host, port=cnf.redis.port)

    # Create mongo connection at startup
    log.info("Setup mongodb connection: %s:%s", cnf.mongodb.host, cnf.mongodb.port)
    MongoDB.setup(host=cnf.mongodb.host, port=cnf.mongodb.port, db_name=cnf.mongodb.database)
    initialize_indexes()

    queue = Queue(cnf.redis.queue, connection=redis)
    worker = SimpleWorker([queue], connection=redis)
    return worker

def create_cron_worker() -> CronScheduler:
    """Start a new cron worker instance."""
    configure_logging(cnf)
    log = logging.getLogger(__name__)
    log.info("Setup redis connection: %s:%s", cnf.redis.host, cnf.redis.port)

    redis = Redis(host=cnf.redis.host, port=cnf.redis.port)
    cron = CronScheduler(connection=redis, logging_level=cnf.log_level)

    # setup periodic tasks
    if cnf.periodic_integrity_check.endabled:
        cron_string = cnf.periodic_integrity_check.cron
        cron.register(tasks.run_data_integrity_check,
                      queue_name=cnf.periodic_integrity_check.queue,
                      cron=cron_string)
        log.info("Scheduling periodic integrity check: %s", cron_string)

    if cnf.cleanup_removed_files.endabled:
        cron_string = cnf.cleanup_removed_files.cron
        cron.register(tasks.cleanup_removed_files,
                      queue_name=cnf.cleanup_removed_files.queue,
                      cron=cron_string)
        log.info("Scheduling cleanup of removed files: %s", cron_string)

    return cron
