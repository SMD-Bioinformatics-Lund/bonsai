"""Functions for migrating the database between versions."""
from typing import Any, Callable
from bson import json_util
import click
import logging

from bonsai_api.crud.utils import get_deprecated_records
from bonsai_api.models.sample import SampleInCreate
from bonsai_api.models.group import GroupInCreate
from bonsai_api.models.group import SCHEMA_VERSION as GROUP_SCHEMA_VERSION
from bonsai_api.crud.sample import update_sample
from bonsai_api.db import Database
from prp.models.sample import SCHEMA_VERSION as SAMPLE_SCHEMA_VERSION
from prp.migration.convert import migrate_result as sample_migrate_result


LOG = logging.getLogger(__name__)
UnformattedResult = dict[str, Any]

class MigrationError(Exception):
    ...


async def migrate_sample_collection(db: Database, backup_path: str | None):
    """Migrate the sample collection bewteen schema versions."""
    if db.sample_collection is None:
        raise ValueError
    samples: list[dict[str, Any]] = await get_deprecated_records(db.sample_collection, SAMPLE_SCHEMA_VERSION)

    # 2 summarize operation
    if len(samples) == 0:
        click.secho("Sample collection is up to date!", fg="green")
        return None

    click.secho(f"Found {click.style(len(samples), fg='cyan', bold=True)} entry to migrate.")

    # Confirm migration
    click.confirm('Do you what to continue?', abort=True)

    # 3 migrate data and validate using the current schema
    migrated_samples: list[SampleInCreate] = [
        SampleInCreate.model_validate(
            sample_migrate_result(sample, validate=False)
        ) for sample in samples
    ]
    # 4 backup old records as json array
    if backup_path is not None:
        click.secho(f"Backing up old entries to: {backup_path}")
        with open(backup_path, 'w', encoding='utf-8') as outf:
            outf.write(json_util.dumps(samples, indent=3))
    # 5 update samples
    click.secho(f"Updating samples in the database")
    for upd_sample in migrated_samples:
        was_updated = update_sample(db, upd_sample)
        if not was_updated:
            raise MigrationError(f"Sample '{upd_sample.sample_id}' was not updated.")


def group_pre_1_to_1(group: UnformattedResult) -> UnformattedResult:
    """Convert group object format from pre-v1 to v1."""
    if 'schema_version' in group:
        raise MigrationError("Invalid schema version - expected undefined field!")

    LOG.info("Migrating to schema version %d", 1)
    upd_group = copy(group)

    # add schema version
    upd_group["schema_version"] = 1

    # replace SampleTableColumnInput objects with 


def v1_to_v2(result: UnformattedResult) -> UnformattedResult:
    """Convert result in json format from v1 to v2."""
    input_schema_version = result["schema_version"]
    if input_schema_version != 1:
        raise ValueError(f"Invalid schema version '{input_schema_version}' expected 1")

    LOG.info("Migrating from v%d to v%d", input_schema_version, 2)
    upd_result = copy(result)
    # split analysis profile into a list and strip white space
    upd_profile: list[str] = [
        prof.strip() for prof in result["pipeline"]["analysis_profile"].split(",")
    ]
    upd_result["pipeline"]["analysis_profile"] = upd_profile
    # get assay from upd_profile
    new_assay: str = next(
        (
            config.profile_array_modifiers[prof]
            for prof in upd_profile
            if prof in config.profile_array_modifiers
        ),
        None,
    )
    upd_result["pipeline"]["assay"] = new_assay
    # add release_life_cycle
    new_release_life_cycle: str = (
        "development" if {"dev", "development"} & set(upd_profile) else "production"
    )
    upd_result["pipeline"]["release_life_cycle"] = new_release_life_cycle
    # update schema version
    upd_result["schema_version"] = 2
    return upd_result



def migrate_group(group):
    """Migrate group documents in the database."""
    ALL_FUNCS: dict[int, Callable[..., UnformattedResult]] = {"pre_1": group_pre_1_to_1}
    import pdb; pdb.set_trace()


async def migrate_group_collection(db: Database, backup_path: str | None):
    if db.sample_group_collection is None:
        raise ValueError
    groups: list[dict[str, Any]] = await get_deprecated_records(db.sample_group_collection, GROUP_SCHEMA_VERSION)

    # 2 summarize operation
    if len(groups) == 0:
        click.secho("Group collection is up to date!", fg="green")
        return None

    click.secho(f"Found {click.style(len(groups), fg='cyan', bold=True)} entry to migrate.")

    # Confirm migration
    click.confirm('Do you what to continue?', abort=True)

    # 3 migrate data and validate using the current schema
    migrated_groups: list[GroupInCreate] = [
        GroupInCreate.model_validate(
            group_migrate_result(group)
        ) for group in groups
    ]
    import pdb; pdb.set_trace()