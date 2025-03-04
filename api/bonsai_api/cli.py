"""Commmand line interface to server component."""

import asyncio
from csv import DictWriter
from logging import getLogger
from typing import Callable
from io import TextIOWrapper

import click
from pymongo.errors import DuplicateKeyError

from .__version__ import VERSION as version
from .auth import generate_random_pwd
from .config import USER_ROLES
from .crud.group import create_group as create_group_in_db
from .crud.sample import get_sample, get_samples, update_sample
from .crud.tags import compute_phenotype_tags
from .crud.user import create_user as create_user_in_db
from .db import verify
from .db.index import INDEXES
from .db.utils import get_db_connection
from .io import sample_to_kmlims
from .models.group import GroupInCreate, pred_res_cols
from .models.sample import SampleInCreate, SampleInDatabase
from .models.user import UserInputCreate

LOG = getLogger(__name__)


@click.group()
@click.version_option(version)
@click.pass_context
def cli(_ctx: click.Context):
    """Bonsai api server"""


@cli.command()
@click.pass_context
@click.option("-p", "--password", default="admin", help="Password of admin user.")
def setup(ctx: click.Context, password: str):
    """Setup a new database instance by creating an admin user and setup indexes."""
    # create collections
    click.secho("Start database setup...", fg="green")
    try:
        ctx.invoke(index)
        ctx.invoke(
            create_user,
            username="admin",
            password=password,
            email="placeholder@mail.com",
            role="admin",
        )
    except Exception as err:
        click.secho(f"An error occurred, {err}", fg="red")
        raise click.Abort()
    finally:
        click.secho("setup complete", fg="green")


@cli.command()
@click.pass_obj
@click.option("-u", "--username", required=True, help="Desired username.")
@click.option("--fname", help="Fist name")
@click.option("--lname", help="Last name")
@click.option("-m", "--email", required=True, help="E-mail.")
@click.option(
    "-p",
    "--password",
    default=generate_random_pwd(),
    help="Desired password (optional).",
)
@click.option(
    "-r",
    "--role",
    required=True,
    type=click.Choice(list(USER_ROLES.keys())),
    help="User role which dictates persmission.",
)
def create_user(
    _ctx: click.Context, username: str, email: str, password: str, role: str, fname: str, lname: str
):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """Create a user account"""
    # create collections
    user = UserInputCreate(
        username=username,
        first_name=fname,
        last_name=lname,
        password=password,
        email=email,
        roles=[role],
    )
    try:
        loop = asyncio.get_event_loop()
        with get_db_connection() as db:
            func = create_user_in_db(db, user)
            loop.run_until_complete(func)
    except DuplicateKeyError as error:
        raise click.UsageError(f'Username "{username}" is already taken') from error
    finally:
        click.secho(f'Successfully created the user "{user.username}"', fg="green")


@cli.command()
@click.pass_obj
@click.option("-i", "--id", 'group_id', required=True, help="Group id")
@click.option("-n", "--name", required=True, help="Group name")
@click.option("-d", "--description", help="Group description")
def create_group(_ctx: click.Context, group_id: str, name: str, description: str | None):  # pylint: disable=unused-argument
    """Create a user account"""
    # create collections
    group_obj = GroupInCreate(
        group_id=group_id,
        display_name=name,
        description=description,
        table_columns=pred_res_cols,
    )
    try:
        loop = asyncio.get_event_loop()
        with get_db_connection() as db:
            func = create_group_in_db(db, group_obj)
            loop.run_until_complete(func)
    except DuplicateKeyError as error:
        raise click.UsageError(f'Group with "{id}" exists already') from error
    finally:
        click.secho(f'Successfully created a group with id: "{id}"', fg="green")


@cli.command()
@click.pass_obj
def index(_ctx: click.Context):  # pylint: disable=unused-argument
    """Create and update indexes used by the mongo database."""
    with get_db_connection() as db:
        for collection_name, indexes in INDEXES.items():
            collection = getattr(db, f"{collection_name}_collection")
            click.secho(f"Creating index for: {collection.name}")
            for idx in indexes:
                collection.create_index(idx["definition"], **idx["options"])


@cli.command()
@click.pass_obj
@click.option("-i", "--sample-id", required=True, help="Sample id")
@click.argument("output", type=click.File("w"), default="-")
def export(_ctx: click.Context, sample_id: str, output: TextIOWrapper) -> None:  # pylint: disable=unused-argument
    """Export resistance results in TSV format."""
    # get sample from database
    loop = asyncio.get_event_loop()
    with get_db_connection() as db:
        func = get_sample(db, sample_id)
        sample = loop.run_until_complete(func)

    try:
        lims_data = sample_to_kmlims(sample)
    except NotImplementedError as error:
        click.secho(error, fg="yellow")
        raise click.Abort(error) from error

    # write lims formatted data
    lims_data.to_csv(output, sep="\t", index=False)
    click.secho(f"Exported {sample_id}", fg="green", err=True)


@cli.command()
@click.pass_obj
def update_tags(_ctx: click.Context):  # pylint: disable=unused-argument
    """Update the tags for samples in the database."""
    LOG.info("Updating tags...")
    loop = asyncio.get_event_loop()
    with get_db_connection() as db:
        func = get_samples(db)
        samples = loop.run_until_complete(func)
    with click.progressbar(
        samples.data, length=samples.records_filtered, label="Updating tags"
    ) as prog_bar:
        for sample in prog_bar:
            upd_tags = compute_phenotype_tags(sample)
            upd_sample = SampleInCreate(**{**sample.model_dump(), "tags": upd_tags})
            # update sample as sync function
            loop = asyncio.get_event_loop()
            func = update_sample(db, upd_sample)
            samples = loop.run_until_complete(func)
    click.secho("Updated tags for all samples", fg="green")


@cli.command()
@click.pass_obj
@click.option(
    "-t",
    "--timeout",
    "redis_timeout",
    type=int,
    default=60,
    help="Timeout limit for requests.",
)
@click.option(
    "-o", "--output", type=click.File("w"), default="-", help="Write report to file."
)
def check_paths(_ctx: click.Context, redis_timeout: int, output: TextIOWrapper) -> None:
    """Check that paths to files are valid."""
    loop = asyncio.get_event_loop()
    # get all samples in the database
    with get_db_connection() as db:
        func = get_samples(db)
        samples: list[SampleInDatabase] = loop.run_until_complete(func)

    # loop over samples and check if paths are valid
    click.secho(f"Checking {samples.records_filtered} samples for invalid paths.")
    with click.progressbar(
        samples.data,
        length=samples.records_filtered,
        label="Checking file paths",
    ) as pbar:
        missing_files: list[verify.MissingFile] = []
        for sample in pbar:
            status: verify.MISSING_FILES = verify.verify_reference_genome(sample)
            if len(status) > 0:
                missing_files.extend(status)

            missing: verify.MissingFile | None = verify.verify_read_mapping(sample)
            if missing is not None:
                missing_files.append(missing)

            # query redis
            redis_funcs: list[Callable[..., verify.MissingFile | None]] = [
                verify.verify_ska_index,
                verify.verify_sourmash_files,
            ]
            for func in redis_funcs:
                missing: verify.MissingFile | None = func(sample, redis_timeout)
                if missing is not None:
                    missing_files.append(missing)

    # write output in csv format if missing paths were identified
    if len(missing_files) == 0:
        click.secho("No samples with invalid paths were identified")
    else:
        writer = DictWriter(output, fieldnames=list(verify.MissingFile.model_fields))
        writer.writeheader()
        for missing_file in missing_files:
            writer.writerow(missing_file.model_dump())
