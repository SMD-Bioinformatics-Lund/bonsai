"""Commmand line interface to server component."""
import asyncio
import json
import random
import string
from logging import getLogger

import click

from .__version__ import VERSION as version
from .config import USER_ROLES
from .crud.user import create_user as create_user_in_db
from .db import db
from .db.index import INDEXES
from .db.utils import connect_to_mongo
from .models.user import UserInputCreate, UserOutputDatabase

LOG = getLogger(__name__)


def _generate_random_pwd(length=15) -> str:
    symbols = string.digits + string.ascii_lowercase + string.ascii_uppercase
    return "".join(random.sample(symbols, length))


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
    click.secho("Start database setup...", fg="green")
    ctx.forward(index)
    ctx.invoke(create_user, username="admin", role="admin")
    click.secho("setup complete", fg="green")


@cli.command()
@click.pass_context
@click.option("-u", "--username", required=True, help="Desired username.")
@click.option(
    "-p",
    "--password",
    default=_generate_random_pwd(),
    help="Desired password (optional).",
)
@click.option(
    "-r",
    "--role",
    required=True,
    type=click.Choice(list(USER_ROLES.keys())),
    help="User role which dictates persmission.",
)
def create_user(ctx, username, password, role):
    """Create a user account"""
    # create collections
    db = ctx.obj["DB"]
    user = UserInputCreate(
        username=username,
        first_name="",
        last_name="",
        password=password,
        email="placeholder@email.com",
        roles=[role],
    )
    loop = asyncio.get_event_loop()
    func = create_user_in_db(db, user)
    loop.run_until_complete(func)
    click.secho(json.dumps(dict(user)))


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
