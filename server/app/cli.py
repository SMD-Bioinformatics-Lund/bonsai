"""Commmand line interface to server component."""
import click
from .db import db
from .db.utils import connect_to_mongo
from .db.index import INDEXES
from .__version__ import VERSION as version


@click.group()
@click.version_option(version)
@click.pass_context
def cli(ctx):
    """Mimer api server"""
    ctx.ensure_object(dict)
    connect_to_mongo()
    db.setup()
    ctx.obj["DB"] = db


@cli.command()
@click.pass_context
def setup(ctx):
    """Setup a new database instance by creating collections and indexes."""
    # create collections
    db = ctx.obj["DB"]


@cli.command()
@click.pass_context
def index(ctx):
    """Create and update indexes used by the mongo database."""
    db = ctx.obj["DB"]
    for collection_name, indexes in INDEXES.items():
        collection = getattr(db, f"{collection_name}_collection")
        click.secho(f"Creating index for: {collection.name}")
        for index in indexes:
            collection.create_index(index["definition"], **index["options"])
