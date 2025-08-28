"""Command line interface for minhash_service."""

import click
import logging

from .db import MongoDB
from .config import settings
from .minhash.models import Event, EventType
from .worker import create_cron_worker, create_minhash_worker
from .factories import create_audit_trail_repo, create_report_repo
from .integrity.checker import check_signature_integrity
from .integrity.report_model import InitiatorType

@click.group()
@click.version_option()
def main():
    """MinHash Service command line interface."""


@main.command()
def run_minhash_worker():
    """Run the RQ worker."""
    app = create_minhash_worker()
    log = logging.getLogger(__name__)
    log.info("Starting worker...")
    app.work()


@main.command()
def run_cron_scheduler():
    """Run the RQ worker."""
    app = create_cron_worker()
    log = logging.getLogger(__name__)
    log.info("Starting maintainance worker...")
    app.start()


@main.command()
@click.option('--store-report', is_flag=True, help="Store the integrity report in the database.")
def check_integrity(store_report: bool):
    """Check integrity of stored signatures."""
    # setup db connection
    MongoDB.setup(host=settings.mongodb.host, port=settings.mongodb.port, db_name=settings.mongodb.database)

    report = check_signature_integrity(initiator=InitiatorType.USER, settings=settings)
    click.secho("Integrity check complete.", fg="green")
    if store_report:
        # store the report in the database
        repo = create_report_repo()
        repo.save(report)

        # report the event in the audit trail
        at = create_audit_trail_repo()
        at.log_event(Event(event_type=EventType.OTHER, details="Integrity check triggered from the CLI completed and report stored."))
    print(report.model_dump_json(indent=2))