"""Command line interface for minhash_service."""

import click

from .config import settings
from .minhash.models import Event, EventType
from .worker import create_app
from .tasks import get_audit_trail_repo
from .integrity.checker import check_signature_integrity
from .integrity.report_model import InitiatorType

@click.group()
@click.version_option()
def main():
    """MinHash Service command line interface."""
    click.echo("MinHash Service CLI")


@main.command()
def run_worker():
    """Run the RQ worker."""
    create_app()

@main.command()
@click.option('--store-report', is_flag=True, help="Store the integrity report in the database.")
def check_integrity(store_report: bool):
    """Check integrity of stored signatures."""
    check_signature_integrity(initiator=InitiatorType.USER, settings=settings)
    click.secho("Integrity check complete.", fg="green")
    if store_report:
        # TODO add initiation of data stores and repositories.
        # store the report in the database

        # report the event in the audit trail
        at = get_audit_trail_repo()
        at.log_event(Event(event_type=EventType.OTHER, details="Integrity check triggered from the CLI completed and report stored."))