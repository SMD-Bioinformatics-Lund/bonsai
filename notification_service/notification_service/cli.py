import logging

import click

from .main import create_worker_app
from .version import __version__


@click.group()
@click.version_option(version=__version__)
def main():
    """MinHash Service command line interface."""


@main.command()
def run_api():
    """Run the notification serivce API."""
    app = create_worker_app()
    log = logging.getLogger(__name__)
    log.info("Starting email service...")
    app.work()
