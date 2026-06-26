"""Command line interface for minhash_service."""

import logging

import click
from redis import Redis
from rq import Queue
from rq.cron import CronScheduler

from minhash_service.core.config import Settings, cnf, configure_logging
from minhash_service.core.factories import (create_audit_trail_repo,
                                            create_report_repo, create_signature_repo,
                                            initialize_indexes)
from minhash_service.core.models import Event, EventType
from minhash_service.db import MongoDB
from minhash_service.integrity.checker import check_signature_integrity
from minhash_service.integrity.report_model import InitiatorType
from minhash_service.tasks import dispatch_job
from minhash_service.tasks.handlers import add_to_index
from minhash_service.tasks.dispatch import SimpleWhitelistWorker

from .utils import format_startup_banner


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
    log.info("\n%s", format_startup_banner(cnf, mode="worker"))

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
    log.info("\n%s", format_startup_banner(cnf, mode="scheduler"))

    # setup redis connection
    redis = Redis(host=cnf.redis.host, port=cnf.redis.port)
    cron = CronScheduler(connection=redis, logging_level=cnf.log_level)

    # setup periodic tasks
    if cnf.periodic_integrity_check.enabled:
        cron_string = cnf.periodic_integrity_check.cron
        cron.register(
            dispatch_job,
            kwargs={"task": "get_integrity_report"},
            queue_name=cnf.periodic_integrity_check.queue,
            cron=cron_string,
        )
        log.info("Scheduling periodic integrity check: %s", cron_string)

    if cnf.cleanup_removed_files.enabled:
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


@main.command()
@click.option("--kmer_size", type=int, help="Specify the k-mer size for filtering signatures (default: from config)")
@click.option("--include-excluded", is_flag=True, help="Include signatures that have been excluded from analysis")
@click.option("--dry-run", is_flag=True, help="Show what would be done without actually recreating the index")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
def recreate_index(kmer_size: int, include_excluded: bool, dry_run: bool, force: bool):
    """Recreate index from records in the database."""
    log = logging.getLogger(__name__)
    
    try:
        MongoDB.setup(
            host=cnf.mongodb.host, port=cnf.mongodb.port, db_name=cnf.mongodb.database
        )
        log.info("MongoDB connection established.")
    except Exception as e:
        log.error("Failed to setup MongoDB: %s", e)
        raise click.ClickException("Database setup failed.")

    try:
        repo = create_signature_repo()
        log.info("Signature repository created.")
    except Exception as e:
        log.error("Failed to create signature repository: %s", e)
        raise click.ClickException("Repository creation failed.")

    # Validate kmer_size
    if kmer_size is not None and kmer_size <= 0:
        raise click.BadParameter("kmer_size must be a positive integer.")

    kmer_size = kmer_size or cnf.kmer_size
    log.info("Using k-mer size: %d", kmer_size)

    # Filter signatures
    try:
        signatures = _filter_signatures_for_index(repo, kmer_size, include_excluded)
        log.info("Filtered %d signatures for indexing.", len(signatures))
    except Exception as e:
        log.error("Failed to filter signatures: %s", e)
        raise click.ClickException("Signature filtering failed.")

    if not signatures:
        log.warning("No signatures found to index.")
        return

    sample_ids = [s.sample_id for s in signatures]

    if dry_run:
        log.info("Dry run: Would recreate index with %d signatures.", len(signatures))
        click.echo(f"Dry run: Would index {len(signatures)} signatures with sample IDs: {sample_ids[:10]}{'...' if len(sample_ids) > 10 else ''}")
        return

    if not force:
        if not click.confirm(f"This will recreate the index with {len(signatures)} signatures. Continue?"):
            log.info("Index recreation cancelled by user.")
            return

    try:
        add_to_index(sample_ids=sample_ids)
        log.info("Index recreated successfully with %d signatures.", len(signatures))
        click.secho("Index recreated successfully.", fg="green")
    except Exception as e:
        log.error("Failed to recreate index: %s", e)
        raise click.ClickException("Index recreation failed.")


def _filter_signatures_for_index(repo, kmer_size: int, include_excluded: bool):
    """Filter signatures for indexing based on kmer_size and exclusion status."""
    signatures = []
    for sig in repo.get_all_signatures():
        if sig.exclude_from_analysis and not include_excluded:
            continue
        if sig.kmer_size == kmer_size:
            signatures.append(sig)
    return signatures