"""Commmand line interface to server component."""

import asyncio
import pathlib
from io import StringIO, TextIOWrapper
from logging import getLogger
from typing import Any, Callable, Literal

import click

from api_client.notification import NotificationClient, EmailCreate
from api_client.audit_log.models import Actor, SourceType
from api_client.audit_log import AuditLogClient

from bonsai_api.__version__ import VERSION as version
from bonsai_api.auth import generate_random_pwd
from bonsai_api.config import USER_ROLES
from bonsai_api.crud.group import create_group as create_group_in_db
from bonsai_api.crud.sample import get_sample, get_samples, update_sample
from bonsai_api.crud.tags import compute_phenotype_tags
from bonsai_api.crud.user import create_user as create_user_in_db
from bonsai_api.db import verify
from bonsai_api.db.index import INDEXES
from bonsai_api.db.utils import get_db_connection
from bonsai_api.lims_export.export import lims_rs_formatter, serialize_lims_results
from bonsai_api.lims_export.config import InvalidFormatError, load_export_config
from bonsai_api.models.group import GroupInCreate, SampleTableColumnDB, pred_res_cols
from bonsai_api.models.sample import MultipleSampleRecordsResponseModel, SampleInCreate
from bonsai_api.models.user import UserInputCreate
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.migrate import migrate_sample_collection, migrate_group_collection, MigrationError
from bonsai_api.config import settings
from pymongo.errors import DuplicateKeyError

from .utils import EmailType, create_missing_file_report

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
    _ctx: click.Context,
    username: str,
    email: str,
    password: str,
    role: str,
    fname: str,
    lname: str,
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
        # build request context
        ctx = ApiRequestContext(actor=Actor(id=username, type=SourceType.USR), metadata={})
        # get audit connnection
        audit_log: AuditLogClient | None = None
        if settings.audit_log_service_api is not None:
            audit_log = AuditLogClient(base_url=str(settings.audit_log_service_api))

        # run cli command
        loop = asyncio.get_event_loop()
        with get_db_connection() as db:
            func = create_user_in_db(db, user, ctx, audit_log)
            loop.run_until_complete(func)
    except DuplicateKeyError as error:
        raise click.UsageError(f'Username "{username}" is already taken') from error
    finally:
        click.secho(f'Successfully created the user "{user.username}"', fg="green")


@cli.command()
@click.pass_obj
@click.option("-i", "--id", "group_id", required=True, help="Group id")
@click.option("-n", "--name", required=True, help="Group name")
@click.option("-d", "--description", help="Group description")
def create_group(
    _ctx: click.Context, group_id: str, name: str, description: str | None
):  # pylint: disable=unused-argument
    """Create a user account"""
    # create collections
    group_obj = GroupInCreate(
        group_id=group_id,
        display_name=name,
        description=description,
        table_columns=[SampleTableColumnDB(id=col.id) for col in pred_res_cols],
        validated_genes=None
    )
    try:
        # build request context
        ctx = ApiRequestContext(actor=Actor(id=group_id, type=SourceType.USR), metadata={})
        # get audit connnection
        audit_log: AuditLogClient | None = None
        if settings.audit_log_service_api is not None:
            audit_log = AuditLogClient(base_url=str(settings.audit_log_service_api))

        loop = asyncio.get_event_loop()
        with get_db_connection() as db:
            func = create_group_in_db(db, group_obj, ctx, audit_log)
            loop.run_until_complete(func)
    except DuplicateKeyError as error:
        raise click.UsageError(f'Group with "{group_id}" exists already') from error
    finally:
        click.secho(f'Successfully created a group with id: "{group_id}"', fg="green")


@cli.command()
@click.pass_obj
def index(_ctx: click.Context):  # pylint: disable=unused-argument
    """Create and update indexes used by the mongo database."""
    with get_db_connection() as db:
        for collection_name, indexes in INDEXES.items():
            collection = getattr(db, f"{collection_name}_collection")
            click.secho(f"Creating index for: {collection.name}")
            for idx in indexes:
                loop = asyncio.get_event_loop()
                func = collection.create_index(idx["definition"], **idx["options"])
                loop.run_until_complete(func)


@cli.command()
@click.pass_obj
@click.option("-i", "--sample-id", required=True, help="Sample id")
@click.option("-e", "--export-cnf", type=click.Path(), help="Optional LIMS export configuration.")
@click.option("-f", "--format", "output_format", type=click.Choice(["csv", "tsv"]), help="Optional LIMS export configuration.")
@click.argument("output", type=click.File("w"), default="-")
def export(
    _ctx: click.Context, sample_id: str, export_cnf: pathlib.Path | None, output_format: Literal["tsv", "csv"], output: TextIOWrapper,
) -> None:  # pylint: disable=unused-argument
    """Export resistance results in TSV format."""
    if export_cnf and not export_cnf.exists():
        raise click.ClickException(f"Configuration file not found: {export_cnf}")

    # get sample from database
    loop = asyncio.get_event_loop()
    with get_db_connection() as db:
        func = get_sample(db, sample_id)
        sample = loop.run_until_complete(func)

    try:
        # load config and cast as pydantic model
        lims_data = None
        conf_obj = load_export_config(export_cnf)
        for cnf in conf_obj:
            if cnf.assay == sample.pipeline.assay:
                lims_data = lims_rs_formatter(sample, cnf)
    except (InvalidFormatError, FileNotFoundError, ValueError) as error:
        click.secho(error, fg="yellow")
        raise click.Abort(error) from error

    if lims_data is None:
        click.secho(f"No configuration for assay {sample.pipeline.assay}", fg="red")
        raise click.Abort()

    # write lims formatted data
    tabular = serialize_lims_results(lims_data, delimiter=output_format)
    output.write(tabular)
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
    "-e",
    "--email",
    "email_addr",
    type=EmailType(),
    multiple=True,
    help="email report to recipient.",
)
@click.option(
    "-o", "--output", type=click.File("w"), default="-", help="Write report to file."
)
def check_paths(
    _ctx: click.Context,
    redis_timeout: int,
    email_addr: list[str],
    output: TextIOWrapper,
) -> None:
    """Check that paths to files are valid."""
    loop = asyncio.get_event_loop()
    # get all samples in the database
    with get_db_connection() as db:
        func = get_samples(db)
        samples: MultipleSampleRecordsResponseModel = loop.run_until_complete(func)

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

    output_ch = StringIO()
    if len(missing_files) == 0:
        print("No samples with invalid paths were identified", file=output_ch)
    else:
        create_missing_file_report(missing_files, file=output_ch)

    if len(email_addr) > 0:
        # send report as email instead of writing to output
        if settings.notification_service_api is None:
            LOG.error("URL to notification service has not been configured, cant send report...")
        else:
            notify = NotificationClient(base_url=str(settings.notification_service_api))
            report = EmailCreate(
                recipient=email_addr, subject="SKA Integrity report", message=output_ch.getvalue()
            )
            notify.send_email(report)
    else:
        output.write(output_ch.getvalue())
    click.secho("Finished validating file paths", fg='green')


@cli.command()
def get_event():
    """Get a events"""
    if settings.audit_log_service_api:
        client = AuditLogClient(base_url=str(settings.audit_log_service_api))
        events = client.get_events()
        click.secho(events)
    else:
        raise ValueError(settings.audit_log_service_api)


@cli.command()
@click.option('-b', '--backup', 'backup_path', type=click.Path(path_type=pathlib.Path), help="Backup samples that will be modified to PATH.")
def migrate_database(backup_path: pathlib.Path | None):
    """Migrate the data to a newer version of the schema."""
    click.secho(f"Preparing to migrate the {click.style('Bonsai', fg='green', bold=True)} database...")
    # 1 query the database for all samples that does not have the current schema version
    loop = asyncio.get_event_loop()
    with get_db_connection() as db:
        try:
            for mig_func in [migrate_sample_collection, migrate_group_collection]:
                loop.run_until_complete(mig_func(db, backup_path))
        except MigrationError as err:
            LOG.error(str(err))
            click.Abort()
        finally:
            click.secho("Finished migrating the database", fg="green")