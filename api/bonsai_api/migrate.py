"""Functions for migrating the database between versions."""

import logging
import pathlib
from copy import copy
from typing import Any, Callable

import click
from bonsai_api.crud.utils import get_deprecated_records
from bonsai_api.db import Database
from bonsai_api.models.sample import SAMPLE_SCHEMA_VERSION, SampleRecordDb
from bonsai_api.models.group import GROUP_SCHEMA_VERSION, GroupInfoCreate
from bson import json_util

LOG = logging.getLogger(__name__)
UnformattedResult = dict[str, Any]


async def migrate_sample_collection(db: Database, backup_path: str | None):
    """Migrate the sample collection bewteen schema versions."""
    if db.sample_collection is None:
        raise ValueError
    samples: list[dict[str, Any]] = await get_deprecated_records(
        db.sample_collection, SAMPLE_SCHEMA_VERSION
    )

    # 2 summarize operation
    if len(samples) == 0:
        click.secho("Sample collection is up to date!", fg="green")
        return None

    click.secho(
        f"Found {click.style(len(samples), fg='cyan', bold=True)} entry to migrate."
    )

    # Confirm migration
    click.confirm("Do you what to continue?", abort=True)

    # 3 migrate data and validate using the current schema
    migrated_samples: list[SampleRecordDb] = []
    raise NotImplementedError("Sample migration function not implemented yet")

    # 4 backup old records as json array
    # if backup_path is not None:
    #     click.secho(f"Backing up old entries to: {backup_path}")
    #     with open(backup_path, "w", encoding="utf-8") as outf:
    #         outf.write(json_util.dumps(samples, indent=3))
    # 5 update samples
    # click.secho(f"Updating samples in the database")
    # for upd_sample in migrated_samples:
    #     was_updated = update_sample(db, upd_sample)
    #     if not was_updated:
    #         raise MigrationError(f"Sample '{upd_sample.sample_id}' was not updated.")


def migrate_group(group: UnformattedResult) -> UnformattedResult:
    """Migrate group documents in the database."""
    ALL_FUNCS: dict[int, Callable[..., UnformattedResult]] = {}

    # apply migrations for v1 and onwards
    for start_version, migration_func in ALL_FUNCS.items():
        if start_version == group["schema_version"]:
            group = migration_func(group)
    return group


async def migrate_group_collection(db: Database, backup_path: pathlib.Path | None):
    if db.sample_group_collection is None:
        raise ValueError
    groups: list[dict[str, Any]] = await get_deprecated_records(
        db.sample_group_collection, GROUP_SCHEMA_VERSION
    )

    # 2 summarize operation
    if len(groups) == 0:
        click.secho("Group collection is up to date!", fg="green")
        return None

    click.secho(
        f"Found {click.style(len(groups), fg='cyan', bold=True)} entry to migrate."
    )

    # Confirm migration
    click.confirm("Do you what to continue?", abort=True)

    # 3 migrate data and validate using the current schema
    migrated_groups: list[GroupInfoCreate] = [
        GroupInfoCreate.model_validate(migrate_group(group)) for group in groups
    ]

    # 4 backup old records as json array
    if backup_path is not None:
        click.secho(f"Backing up old entries to: {backup_path}")
        new_path = backup_path.joinpath("groups.backup.json")
        with open(new_path, "w", encoding="utf-8") as outf:
            outf.write(json_util.dumps(groups, indent=3))

    # 5 groups in database
    click.secho("Updating groups in the database")
    for upd_group in migrated_groups:
        ...
        # was_updated = await update_group(db, upd_group.group_id, upd_group)
        # if not was_updated:
        #     raise MigrationError(f"Sample '{upd_group.group_id}' was not updated.")


migration_functions: list[Callable[..., Any]] = [
    migrate_sample_collection,
    migrate_group_collection,
]
