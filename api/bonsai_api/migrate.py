"""Functions for migrating the database between versions."""

import logging
import pathlib
from copy import copy
from typing import Any, Callable

import click
from bonsai_api.crud.group import update_group
from bonsai_api.crud.sample import update_sample
from bonsai_api.crud.utils import get_deprecated_records
from bonsai_api.db import Database
from bonsai_api.models.group import SCHEMA_VERSION as GROUP_SCHEMA_VERSION
from bonsai_api.models.group import (GroupInCreate, SampleTableColumnDB,
                                     pred_res_cols, qc_cols)
from bonsai_api.models.sample import SampleInCreate
from bson import json_util
from prp.migration.convert import migrate_result as sample_migrate_result
from prp.models.sample import SCHEMA_VERSION as SAMPLE_SCHEMA_VERSION

LOG = logging.getLogger(__name__)
UnformattedResult = dict[str, Any]


class MigrationError(Exception): ...


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
    migrated_samples: list[SampleInCreate] = [
        SampleInCreate.model_validate(sample_migrate_result(sample, validate=False))
        for sample in samples
    ]
    # 4 backup old records as json array
    if backup_path is not None:
        click.secho(f"Backing up old entries to: {backup_path}")
        with open(backup_path, "w", encoding="utf-8") as outf:
            outf.write(json_util.dumps(samples, indent=3))
    # 5 update samples
    click.secho(f"Updating samples in the database")
    for upd_sample in migrated_samples:
        was_updated = update_sample(db, upd_sample)
        if not was_updated:
            raise MigrationError(f"Sample '{upd_sample.sample_id}' was not updated.")


def group_pre_1_to_1(group: UnformattedResult) -> UnformattedResult:
    """Convert group object format from pre-v1 to v1."""
    if "schema_version" in group:
        raise MigrationError("Invalid schema version - expected undefined field!")

    LOG.info("Migrating to schema version %d", 1)
    upd_group = copy(group)

    # add schema version
    upd_group["schema_version"] = "1"

    # build a uniqe index of all valid columns
    all_valid_cols: list[str] = list({col.id for col in pred_res_cols + qc_cols})
    ID_MIGRATION_TBL = {
        "qc": "qc_status",
        "profile": "analysis_profile",
        "mlst": "mlst_typing",
        "stx": "stx_typing",
        "oh": "oh_typing",
        "missing_loci": "cgmlst_missing_loci",
    }

    # replace SampleTableColumnInput objects with the id
    upd_col_def: list[str] = []
    for col in upd_group["table_columns"]:
        upd_id = ID_MIGRATION_TBL.get(col["id"], col["id"])
        if upd_id not in all_valid_cols:
            LOG.warning("Failed to migrate column with %s", upd_id)
            continue
        upd_col_def.append(upd_id)
    upd_col_def: list[str] = [
        SampleTableColumnDB(id=col["id"]) for col in upd_group["table_columns"]
    ]
    assert all([isinstance(col, str) and len(col) > 0 for col in upd_col_def])

    upd_group["table_columns"] = upd_col_def
    return upd_group


def migrate_group(group: UnformattedResult) -> UnformattedResult:
    """Migrate group documents in the database."""
    ALL_FUNCS: dict[int, Callable[..., UnformattedResult]] = {}

    # for migrating pre-version 1 data
    if "schema_version" not in group:
        group = group_pre_1_to_1(group)

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
    migrated_groups: list[GroupInCreate] = [
        GroupInCreate.model_validate(migrate_group(group)) for group in groups
    ]

    # 4 backup old records as json array
    if backup_path is not None:
        click.secho(f"Backing up old entries to: {backup_path}")
        new_path = backup_path.joinpath("groups.backup.json")
        with open(new_path, "w", encoding="utf-8") as outf:
            outf.write(json_util.dumps(groups, indent=3))

    # 5 groups in database
    click.secho(f"Updating samples in the database")
    for upd_group in migrated_groups:
        was_updated = await update_group(db, upd_group.group_id, upd_group)
        if not was_updated:
            raise MigrationError(f"Sample '{upd_group.group_id}' was not updated.")
