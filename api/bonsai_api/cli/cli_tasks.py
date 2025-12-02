import logging
from csv import DictWriter
from io import StringIO
from pathlib import Path
from typing import Any, Literal

from api_client.audit_log import AuditLogClient
from api_client.audit_log.models import Actor, SourceType
from bonsai_api.config import settings
from bonsai_api.crud.group import create_group as create_group_in_db
from bonsai_api.crud.sample import get_sample, get_samples, update_sample
from bonsai_api.crud.tags import compute_phenotype_tags
from bonsai_api.crud.user import create_user as create_user_in_db
from bonsai_api.db import verify
from bonsai_api.db.index import INDEXES
from bonsai_api.db.utils import get_db_connection
from bonsai_api.db.verify import MissingFile
from bonsai_api.lims_export.config import load_export_config
from bonsai_api.lims_export.export import lims_rs_formatter, serialize_lims_results
from bonsai_api.migrate import migration_functions
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.group import GroupInCreate, GroupInfoDatabase
from bonsai_api.models.sample import (
    MultipleSampleRecordsResponseModel,
    SampleInCreate,
    SampleInDatabase,
)
from bonsai_api.models.user import UserInputCreate, UserOutputDatabase

LOG = logging.getLogger(__name__)


def _get_audit_log_client() -> AuditLogClient | None:
    """Initialize audit log client if service URL is configured."""
    if settings.audit_log_service_api is None:
        return None
    return AuditLogClient(base_url=str(settings.audit_log_service_api))


async def run_create_user(user_obj: UserInputCreate) -> UserOutputDatabase:
    """Create a user in the database.

    Args:
        user_obj: User creation request data.

    Returns:
        UserOutputDatabase: The created user object.

    Raises:
        DocumentExistsError: If username already exists.
        DatabaseOperationError: If database operation fails.
        ValueError: If user_obj is invalid.
    """
    ctx = ApiRequestContext(
        actor=Actor(id=user_obj.username, type=SourceType.USR), metadata={}
    )
    audit_log = _get_audit_log_client()
    LOG.info("Creating user: %s", user_obj.username)
    async with get_db_connection() as db:
        return await create_user_in_db(db, user_obj, ctx, audit_log)


async def run_create_group(group_obj: GroupInCreate) -> GroupInfoDatabase:
    """Create a group in the database.

    Args:
        group_obj: Group creation request data.

    Returns:
        GroupInfoDatabase: The created group object.
    """
    ctx = ApiRequestContext(
        actor=Actor(id="cli_user", type=SourceType.USR), metadata={}
    )
    audit_log = _get_audit_log_client()
    LOG.info("Creating group: %s", group_obj.group_id)
    async with get_db_connection() as db:
        return await create_group_in_db(db, group_obj, ctx, audit_log)


async def run_create_index(col_name: str, indexes: list[dict[str, Any]]) -> None:
    """Create database indexes."""
    valid_collections = list(INDEXES.keys())
    if col_name not in valid_collections:
        raise ValueError(f"Unknown collection: {col_name}")

    async with get_db_connection() as db:
        collection = getattr(db, f"{col_name}_collection")
        for idx in indexes:
            await collection.create_index(idx["definition"], **idx["options"])


async def run_get_samples() -> MultipleSampleRecordsResponseModel:
    """CLI helper to get all samples from the database."""
    async with get_db_connection() as db:
        return await get_samples(db)


async def run_update_tag(sample: SampleInDatabase) -> bool:
    """Update tag of a sample."""
    async with get_db_connection() as db:
        upd_tags = compute_phenotype_tags(sample)
        upd_sample = SampleInCreate(**{**sample.model_dump(), "tags": upd_tags})
        # update sample as sync function
        return await update_sample(db, upd_sample)


async def run_migrate_database(backup_path: Path | None = None) -> None:
    """Helper for running migration functions."""
    async with get_db_connection() as db:
        for mig_func in migration_functions:
            await mig_func(db, backup_path)


async def run_lims_export(
    sample_id: str,
    export_cnf: Path,
    output_format: Literal["csv", "tsv"],
) -> str:
    """Return LIMS-formatted export as a string.

    Raises:
        EntryNotFound: if sample not found
        InvalidFormatError, FileNotFoundError, ValueError: config/format related
        DatabaseOperationError: DB-level problems
    """
    async with get_db_connection() as db:
        sample = await get_sample(db, sample_id)

    conf_obj = load_export_config(export_cnf)  # may raise
    lims_data = None
    for cnf in conf_obj:
        if cnf.assay == sample.pipeline.assay:
            lims_data = lims_rs_formatter(sample, cnf)
            break

    if lims_data is None:
        raise ValueError(f"No configuration for assay {sample.pipeline.assay}")

    tabular = serialize_lims_results(lims_data, delimiter=output_format)
    return tabular


async def run_check_paths(redis_timeout: int) -> dict:
    """Check samples for missing files and return a report.

    Returns a dict with keys:
      - 'report': CSV/text report as string
      - 'records_filtered': number of samples checked
      - 'missing_files': list of MissingFile objects
    """
    async with get_db_connection() as db:
        samples = await get_samples(db)

    missing_files: list[MissingFile] = []
    for sample in samples.data:
        status = verify.verify_reference_genome(sample)
        if len(status) > 0:
            missing_files.extend(status)

        missing = verify.verify_read_mapping(sample)
        if missing is not None:
            missing_files.append(missing)

        # query redis-backed checks
        redis_funcs = [verify.verify_ska_index, verify.verify_sourmash_files]
        for func in redis_funcs:
            missing = func(sample, redis_timeout)
            if missing is not None:
                missing_files.append(missing)

    output_ch = StringIO()
    if len(missing_files) == 0:
        LOG.info("No samples with invalid paths were identified")
        print("No samples with invalid paths were identified", file=output_ch)
    else:
        # write CSV report
        fieldnames = list(MissingFile.model_fields)
        writer = DictWriter(output_ch, fieldnames=fieldnames)
        writer.writeheader()
        for mf in missing_files:
            writer.writerow(mf.model_dump())

    return {
        "report": output_ch.getvalue(),
        "records_filtered": getattr(samples, "records_filtered", len(samples.data)),
        "missing_files": missing_files,
    }
