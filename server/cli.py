"""cgWIZ server command line interface"""

import click
import logging
from .__version__ import VERSION as version


LOG = logging.getLogger(__name__)

@click.group(
    add_default_commands=False,
    add_version_option=False,
)
@click.version_option(version)
def cli(*args, **kwargs):
    """Management of cgWIZ application."""
    pass


@cli.command()
@cli.argument('sample-sheet', type=click.File())
def load(sample_sheet):
    """Load new samples into the database"""
    LOG.info(f'got file {sample_sheet.name}')
