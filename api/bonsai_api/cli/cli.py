"""Commmand line interface to server component."""

import pathlib
from io import TextIOWrapper
from logging import getLogger
from typing import Literal

import click
from api_client.audit_log import AuditLogClient
from api_client.notification import EmailCreate, NotificationClient
from bonsai_api.__version__ import VERSION as version
from bonsai_api.auth import generate_random_pwd
from bonsai_api.config import USER_ROLES, settings
from bonsai_api.crud.errors import EntryNotFound
from bonsai_api.db.index import INDEXES
from bonsai_api.lims_export.config import InvalidFormatError
from bonsai_api.migrate import MigrationError
from bonsai_api.models.group import GroupInCreate, SampleTableColumnDB, pred_res_cols
from bonsai_api.models.user import UserInputCreate
from mongomock import DuplicateKeyError

from .cli_tasks import (
    run_check_paths,
    run_create_group,
    run_create_index,
    run_create_user,
    run_get_samples,
    run_lims_export,
    run_migrate_database,
    run_update_tag,
)
from .utils import EmailType, run_async

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
    user = UserInputCreate(
        username=username,
        first_name=fname,
        last_name=lname,
        password=password,
        email=email,
        roles=[role],
    )
    try:
        run_async(run_create_user(user))
    except DuplicateKeyError as error:
        raise click.UsageError(
            f'Username "{user.username}" is already taken'
        ) from error
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
        validated_genes=None,
    )
    try:
        run_async(run_create_group(group_obj))
    except DuplicateKeyError as error:
        raise click.UsageError(
            f'Group with ID "{group_obj.group_id}" already exists'
        ) from error
    click.secho(f'Successfully created the group "{group_obj.group_id}"', fg="green")


@cli.command()
@click.pass_obj
def index(_ctx: click.Context):  # pylint: disable=unused-argument
    """Create and update indexes used by the mongo database."""
    for collection_name, indexes in INDEXES.items():
        click.secho(f"Creating index for: {collection_name}")
        run_async(run_create_index(collection_name, indexes))
    click.secho("Database indexes created successfully", fg="green")


@cli.command()
@click.pass_obj
@click.option("-i", "--sample-id", required=True, help="Sample id")
@click.option(
    "-e", "--export-cnf", type=click.Path(), help="Optional LIMS export configuration."
)
@click.option(
    "-f",
    "--format",
    "output_format",
    type=click.Choice(["csv", "tsv"]),
    help="Optional LIMS export configuration.",
)
@click.argument("output", type=click.File("w"), default="-")
def export(
    _ctx: click.Context,
    sample_id: str,
    export_cnf: pathlib.Path | None,
    output_format: Literal["tsv", "csv"],
    output: TextIOWrapper,
) -> None:  # pylint: disable=unused-argument
    """Export resistance results in TSV format."""
    export_path = pathlib.Path(export_cnf) if export_cnf else None
    if export_path and not export_path.exists():
        raise click.ClickException(f"Configuration file not found: {export_cnf}")

    try:
        tabular = run_async(run_lims_export(sample_id, export_path, output_format))
    except (InvalidFormatError, FileNotFoundError, ValueError) as error:
        click.secho(error, fg="yellow")
        raise click.Abort(error)
    except EntryNotFound as error:
        raise click.ClickException(f"Sample not found: {sample_id}") from error

    output.write(tabular)
    click.secho(f"Exported {sample_id}", fg="green", err=True)


@cli.command()
@click.pass_obj
def update_tags(_ctx: click.Context):  # pylint: disable=unused-argument
    """Update the tags for samples in the database."""
    samples = run_async(run_get_samples())
    with click.progressbar(
        samples.data, length=samples.records_filtered, label="Updating tags"
    ) as prog_bar:
        for sample in prog_bar:
            run_async(run_update_tag(sample))
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
    result = run_async(run_check_paths(redis_timeout))

    report = result.get("report", "")
    records = result.get("records_filtered", 0)

    click.secho(f"Checking {records} samples for invalid paths.")
    if len(result.get("missing_files", [])) == 0:
        output.write(report)
    else:
        if len(email_addr) > 0:
            # send report as email instead of writing to output
            if settings.notification_service_api is None:
                LOG.error(
                    "URL to notification service has not been configured, cant send report..."
                )
            else:
                notify = NotificationClient(
                    base_url=str(settings.notification_service_api)
                )
                email = EmailCreate(
                    recipient=email_addr,
                    subject="SKA Integrity report",
                    message=report,
                )
                notify.send_email(email)
        else:
            output.write(report)

    click.secho("Finished validating file paths", fg="green")


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
@click.option(
    "-b",
    "--backup",
    "backup_path",
    type=click.Path(path_type=pathlib.Path),
    help="Backup samples that will be modified to PATH.",
)
def migrate_database(backup_path: pathlib.Path | None):
    """Migrate the data to a newer version of the schema."""
    click.secho(
        f"Preparing to migrate the {click.style('Bonsai', fg='green', bold=True)} database..."
    )
    try:
        run_async(run_migrate_database(backup_path))
    except MigrationError as err:
        LOG.error(str(err))
        raise click.Abort()
    finally:
        click.secho("Finished migrating the database", fg="green")
