"""Command line interface for minhash_service."""

import logging

import click
from redis import Redis
from rq import Queue
from rq.cron import CronScheduler

from minhash_service.core.config import Settings, cnf, configure_logging
from minhash_service.core.factories import (
    create_audit_trail_repo,
    create_report_repo,
    initialize_indexes,
)
from minhash_service.core.models import Event, EventType
from minhash_service.db import MongoDB
from minhash_service.integrity.checker import check_signature_integrity
from minhash_service.integrity.report_model import InitiatorType
from minhash_service.tasks import dispatch_job
from minhash_service.tasks.dispatch import SimpleWhitelistWorker


def _setup_logging(settings: Settings) -> logging.Logger:
    configure_logging(settings)
    log = logging.getLogger(__name__)
    log.info("Setup redis connection: %s:%s", cnf.redis.host, cnf.redis.port)
    return log


@click.group()
@click.version_option()
def main():
    """MinHash Service command line interface."""


@main.command()
def run_minhash_worker():
    """Run the RQ worker."""
    log = _setup_logging(cnf)

    # Create mongo connection at startup
    log.info("Setup mongodb connection: %s:%s", cnf.mongodb.host, cnf.mongodb.port)
    MongoDB.setup(
        host=cnf.mongodb.host, port=cnf.mongodb.port, db_name=cnf.mongodb.database
    )
    initialize_indexes()

    # setup redis connection
    redis = Redis(host=cnf.redis.host, port=cnf.redis.port)
    queue = Queue(cnf.redis.queue, connection=redis)
    app = SimpleWhitelistWorker([queue], connection=redis)
    log.info("Starting worker...")
    app.work()


@main.command()
def run_cron_scheduler():
    """Run the RQ worker."""
    log = _setup_logging(cnf)
    # setup redis connection
    redis = Redis(host=cnf.redis.host, port=cnf.redis.port)
    cron = CronScheduler(connection=redis, logging_level=cnf.log_level)

    # setup periodic tasks
    if cnf.periodic_integrity_check.endabled:
        cron_string = cnf.periodic_integrity_check.cron
        cron.register(
            dispatch_job,
            kwargs={"task": "get_integrity_report"},
            queue_name=cnf.periodic_integrity_check.queue,
            cron=cron_string,
        )
        log.info("Scheduling periodic integrity check: %s", cron_string)

    if cnf.cleanup_removed_files.endabled:
        cron_string = cnf.cleanup_removed_files.cron
        cron.register(
            dispatch_job,
            kwargs={"task": "cleanup_removed_files"},
            queue_name=cnf.cleanup_removed_files.queue,
            cron=cron_string,
        )
        log.info("Scheduling cleanup of removed files: %s", cron_string)

    log.info("Starting maintainance worker...")
    cron.start()


@main.command()
@click.option(
    "--store-report", is_flag=True, help="Store the integrity report in the database."
)
def check_integrity(store_report: bool):
    """Check integrity of stored signatures."""
    # setup db connection
    MongoDB.setup(
        host=cnf.mongodb.host, port=cnf.mongodb.port, db_name=cnf.mongodb.database
    )

    report = check_signature_integrity(initiator=InitiatorType.USER, settings=cnf)
    click.secho("Integrity check complete.", fg="green")
    if store_report:
        # store the report in the database
        repo = create_report_repo()
        repo.save(report)

        # report the event in the audit trail
        at = create_audit_trail_repo()
        at.log_event(
            Event(
                event_type=EventType.OTHER,
                details="Integrity check triggered from the CLI completed and report stored.",
            )
        )
    print(report.model_dump_json(indent=2))
