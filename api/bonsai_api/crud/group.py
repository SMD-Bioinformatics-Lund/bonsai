"""Functions for conducting CURD operations on group collection"""

import logging
from typing import Any

from api.bonsai_api.models.user import UserContext
from api_client.audit_log.client import AuditLogClient
from api_client.audit_log.models import SourceType, Subject
from bonsai_api.db import Database
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.group import (
    GroupAllowed,
    GroupCore,
    GroupInfoOut,
    GroupListResponse,
    GroupPresets,
    GroupRecordDb,
    GroupUpdate,
    GroupAllowedUpdate,
    GroupPresetIn,
    GroupInfoCreate,
    Visibility
)
from bonsai_api.models.sample import SampleSummary
from bonsai_api.utils import get_timestamp
from pydantic import ValidationError
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

from .errors import DatabaseOperationError, EntryNotFound
from .utils import audit_event_context, check_groups_exists, managed_transaction
from .memberships import remove_memberships, get_samples_by_group_ids
from .builder.group import build_group_visibility_match_stage, build_single_group_pipeline, group_project_stage
from .builder.helpers import build_facet_pagination, build_sort_stage
from .builder.types import PipelineStages
from .builder.summary_manifest import MANIFEST

LOG = logging.getLogger(__name__)


def _validate_presets_and_default(presets_in: list[GroupPresetIn] | None, default_pid: str | None) -> None:
    """Validate preset uniqueness and that default pid is present when given."""
    presets_in = presets_in or []
    preset_ids = [p.preset_id for p in presets_in]
    if len(preset_ids) != len(set(preset_ids)):
        raise ValueError("Duplicate preset ids provided in presets")
    if default_pid and default_pid not in preset_ids:
        raise ValueError("default_preset_id must match one of the provided presets")


def _validate_allowed_columns(allowed_columns: list[str] | None) -> None:
    """Validate allowed column IDs against the manifest."""
    if allowed_columns is None:
        return
    if not all(isinstance(c, str) for c in allowed_columns):
        raise ValueError("allowed_columns must be a list of strings")
    manifest_column_ids = {col.id for col in MANIFEST.columns}
    for col in allowed_columns:
        if col not in manifest_column_ids:
            raise ValueError(f"Invalid column id in allowed_columns: {col}")


def _build_group_payload(group_record: GroupInfoCreate, owner_id: str | None) -> GroupRecordDb:
    """Build GroupRecordDb representation from create payload."""
    core = GroupCore(
        group_id=group_record.group_id,
        display_name=group_record.display_name,
        description=group_record.description,
        visibility=group_record.visibility,
        owner_id=owner_id,
    )
    presets_obj = GroupPresets(
        default_preset_id=group_record.default_preset_id,
        items=group_record.presets or [],
    )
    allowed_cols = GroupAllowed(column_ids=group_record.allowed_columns or [])
    return GroupRecordDb(
        core=core,
        invited_users=group_record.invited_users or [],
        allowed_columns=allowed_cols,
        presets=presets_obj,
    )


async def get_groups(
    db: Database,
    *,
    offset: int = 0,
    limit: int | None = None,
    sort: str | None = None,
    user_id: str | None = None,
    user_roles: list[str] | None = None,
    session: Any = None,
) -> GroupListResponse:
    """Get collections from database.

    Retrieve groups with optional filtering, projection and pagination.
    - limit: max results to return; use None for no limit (but avoid for large collections).
    - offset: documents to skip (offset pagination).
    - sort: fieldname to sort by, use prefix - to indicate descending.
    - user_id: if provided, filter groups based on user access.
    - user_roles: roles of the user for access control.
    """
    try:
        data_pipeline: PipelineStages = []

        if user_id is not None and "admin" not in (user_roles or []):
            # non-admin users only see public groups, or those they own / are invited to
            data_pipeline.append(build_group_visibility_match_stage(user_id))

        # format the group data
        data_pipeline.append(group_project_stage(include_allowed=True, include_presets=True))
        
        if sort:
            allowed_sort_fields = {
                "group_id",
                "display_name",
                "sample_count",
                "created_at",
                "modified_at",
            }
            data_pipeline.append(build_sort_stage(sort, allowed_sort_fields))

        # add pagination facet
        data_pipeline.append(build_facet_pagination(offset, limit))
        
        agg_cursor = await db.sample_group_collection.aggregate(data_pipeline, session=session)
        results = await agg_cursor.to_list(None)
    except PyMongoError as pme:
        LOG.error("MongoDB error while retrieving groups: %s", str(pme))
        raise DatabaseOperationError(
            f"Database error occurred while retrieving groups: {str(pme)}"
        ) from pme
    except ValueError as ve:
        LOG.error("Value error while building group retrieval pipeline: %s", str(ve))
        raise

    # process the data
    facet = results[0] if results else {}

    validated: list[GroupInfoOut] = []
    raw_data = facet.get("data", [])
    for doc in raw_data:
        try:
            validated.append(GroupInfoOut.model_validate(doc))
        except ValidationError as ve:
            LOG.error("Skipping invalid group document: %s", str(ve))
            continue
    records_total = facet.get("records_total", [])
    return GroupListResponse(data=validated, records_total=records_total[0]["count"] if records_total else len(validated))


async def get_group(
    db: Database,
    group_id: str,
    *,
    user_id: str | None = None, 
    user_roles: list[str] | None = None, 
    session: Any = None
) -> GroupInfoOut:
    """Retrieve a single group by `group_id` with access control.

    - Admins: bypass visibility restrictions.
    - Non-admins: must be public OR owner OR invited (missing visibility treated as public).
    - Returns `GroupInfoOut` or raises `EntryNotFound` (404 semantics).
    """
    if not group_id or not isinstance(group_id, str):
        raise ValueError(f"Invalid group_id: must be a non-empty string, got {group_id}")

    try:
        data_pipeline: PipelineStages = [
            {"$match": {"core.group_id": group_id}},
        ]
        if user_id is not None and "admin" not in (user_roles or []):
            # non-admin users only see public groups, or those they own / are invited to
            data_pipeline.append(build_group_visibility_match_stage(user_id))

        # add data fields
        data_pipeline.append(group_project_stage(include_presets=True))

        agg_cursor = await db.sample_group_collection.aggregate(data_pipeline, session=session)
        docs = await agg_cursor.to_list(1)
        if not docs:
            # Either the group doesn't exist OR the caller isn't allowed to see it.
            raise EntryNotFound(group_id)

        return GroupInfoOut.model_validate(docs[0])
    except PyMongoError as pme:
        LOG.error("MongoDB error while retrieving group: %s", str(pme))
        raise DatabaseOperationError(
            f"Database error occurred while retrieving group: {str(pme)}"
        ) from pme
    except ValidationError as ve:
        LOG.error(
            "Group %s caused validation error: %s",
            group_id, ve,
        )
        raise


async def _fetch_group_minimal(db: Database, group_id: str, session: Any = None) -> dict[str, Any] | None:
    """Fetch minimal fields required for access checks.

    Tries both top-level `group_id` and `core.group_id` to remain compatible with older documents.
    """
    q = {"$or": [{"group_id": group_id}, {"core.group_id": group_id}]}
    proj = {"_id": 0, "core.owner_id": 1, "core.visibility": 1, "invited_users": 1, "group_id": 1}
    return await db.sample_group_collection.find_one(q, proj, session=session)


async def check_group_read_permission(
    db: Database, group_id: str, user_id: str | None, user_roles: list[str] | None = None, session: Any = None
) -> bool:
    """Return True if the given user can read the group, False otherwise.

    Policy: public groups are readable by anyone. Private groups are readable by owner, invited users or admins.
    """
    user_roles = user_roles or []
    doc = await _fetch_group_minimal(db, group_id, session=session)
    if not doc:
        return False

    visibility = doc.get("core", {}).get("visibility") or doc.get("visibility") or "public"
    if visibility == "public":
        return True

    # private
    owner = doc.get("core", {}).get("owner_id")
    invited = doc.get("invited_users") or []
    if user_id and (user_id == owner or user_id in invited):
        return True

    if "admin" in (user_roles or []):
        return True

    return False


async def check_group_manage_permission(
    db: Database, group_id: str, user_id: str | None, user_roles: list[str] | None = None, session: Any = None
) -> bool:
    """Return True if the given user can manage (modify) the group (owner or admin)"""
    user_roles = user_roles or []
    doc = await _fetch_group_minimal(db, group_id, session=session)
    if not doc:
        return False
    owner = doc.get("core", {}).get("owner_id")
    if user_id and user_id == owner:
        return True
    if "admin" in (user_roles or []):
        return True
    return False


async def create_group(
    db: Database,
    group_record: GroupInfoCreate,
    *,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
    creator: UserContext | None = None,
    session: Any = None,
) -> GroupInfoOut:
    """Create a new group document.

    Notes:
    - Prefer providing `creator: UserContext` to reduce separate args (owner_id, user_roles).
    - Validation and payload assembly are delegated to helpers to keep this function small.
    """
    _validate_presets_and_default(group_record.presets, group_record.default_preset_id)
    _validate_allowed_columns(group_record.allowed_columns)

    # enforce visibility/invite rules: only owner or admin can create private groups
    if group_record.visibility == Visibility.PRIVATE and not creator.user_id and not creator.is_admin():
        raise ValueError("Only owner or admin may create a private group")

    payload = _build_group_payload(group_record, creator.user_id)

    event_subject = Subject(id=group_record.group_id, type=SourceType.USR)
    with audit_event_context(audit, "create_group", ctx, event_subject):
        try:
            doc = await db.sample_group_collection.insert_one(payload.model_dump(mode="json"), session=session)
            LOG.info("Created group %s with id %s", group_record.group_id, str(doc.inserted_id))
            return GroupInfoOut(
                group_id=group_record.group_id,
                display_name=group_record.display_name,
                description=group_record.description,
                sample_count=0,
                default_preset_id=group_record.default_preset_id,
            )
        except DuplicateKeyError as dke:
            LOG.error("Duplicate key error while creating group: %s", str(dke))
            raise DatabaseOperationError(
                f"Group with id {group_record.group_id} already exists."
            ) from dke
        except PyMongoError as pme:
            LOG.error("MongoDB error while creating group: %s", str(pme))
            raise DatabaseOperationError(
                f"Database error occurred while creating group: {str(pme)}"
            ) from pme
        except ValidationError as ve:
            LOG.error("Validation error while creating group: %s", str(ve))
            raise ValueError(
                f"Invalid data provided for creating group: {str(ve)}"
            ) from ve


async def delete_group(
    db: Database,
    group_id: str,
    *,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> None | int:
    """Delete group with group_id from database."""
    if not group_id:
        return

    event_subject = Subject(id=group_id, type=SourceType.USR)
    meta = {"group_id": group_id}
    with audit_event_context(audit, "delete_group", ctx, event_subject, metadata=meta):
        async with managed_transaction(db.client) as session:
            try:
                missing = await check_groups_exists(db, [group_id], session=session)
                if missing:
                    raise EntryNotFound(group_id)

                # Remove group from stored memberships
                edges = await get_samples_by_group_ids([group_id], db=db, session=session)
                await remove_memberships(edges, db=db, session=session)

                # Remove group document
                group_res = await db.sample_group_collection.delete_one(
                    {"group_id": group_id}, session=session
                )
                if group_res.deleted_count == 0:
                    raise EntryNotFound(group_id)

                return group_res.deleted_count
            except PyMongoError as pme:
                LOG.error("MongoDB error while deleting group: %s", str(pme))
                raise DatabaseOperationError(
                    f"Database error occurred while deleting group: {str(pme)}"
                ) from pme


async def update_group(
    db: Database,
    group_id: str,
    group_record: GroupInfoCreate,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> GroupInfoOut:
    """Update information of group."""
    payload = group_record.model_dump(mode="json")
    if not payload:
        # Nothing to update, return current document
        exsting = await get_group(db, group_id)
        if not exsting:
            raise EntryNotFound(group_id)
        return GroupInfoOut.model_validate(exsting)

    payload["modified_at"] = get_timestamp()
    # update info in database
    event_subject = Subject(id=group_id, type=SourceType.USR)
    with audit_event_context(audit, "update_group", ctx, event_subject):
        try:
            updated = await db.sample_group_collection.find_one_and_update(
                {"group_id": group_id},
                {"$set": payload},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as pme:
            LOG.error("MongoDB error while updating group: %s", str(pme))
            raise DatabaseOperationError(
                f"Database error occurred while updating group: {str(pme)}"
            ) from pme

        if not updated:
            raise EntryNotFound(group_id)

    return GroupInfoOut.model_validate(updated)


async def update_group_core(
    db: Database,
    group_id: str,
    group_update: "GroupUpdate",
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> GroupInfoOut:
    """Update mutable group core fields (display_name, description)."""
    payload = group_update.model_dump(exclude_none=True)
    if not payload:
        return GroupInfoOut.model_validate(await get_group(db, group_id))

    payload["modified_at"] = get_timestamp()
    event_subject = Subject(id=group_id, type=SourceType.USR)
    with audit_event_context(audit, "update_group_core", ctx, event_subject):
        try:
            updated = await db.sample_group_collection.find_one_and_update(
                {"group_id": group_id},
                {"$set": {f"core.{k}": v for k, v in payload.items()}},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as pme:
            LOG.error("MongoDB error while updating group core: %s", str(pme))
            raise DatabaseOperationError(
                f"Database error occurred while updating group core: {str(pme)}"
            ) from pme

        if not updated:
            raise EntryNotFound(group_id)

    return GroupInfoOut.model_validate(updated)


async def set_allowed_columns(
    db: Database,
    group_id: str,
    allowed: "GroupAllowedUpdate",
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> GroupInfoOut:
    """Set allowed columns for a group."""
    payload = {"allowed_columns": {"column_ids": allowed.column_ids}}
    payload["modified_at"] = get_timestamp()

    event_subject = Subject(id=group_id, type=SourceType.USR)
    with audit_event_context(audit, "set_allowed_columns", ctx, event_subject):
        try:
            updated = await db.sample_group_collection.find_one_and_update(
                {"group_id": group_id},
                {"$set": payload},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as pme:
            LOG.error("MongoDB error while setting allowed columns: %s", str(pme))
            raise DatabaseOperationError(
                f"Database error occurred while setting allowed columns: {str(pme)}"
            ) from pme

        if not updated:
            raise EntryNotFound(group_id)

    return GroupInfoOut.model_validate(updated)


async def upsert_preset(
    db: Database,
    group_id: str,
    preset: "GroupPresetIn",
    set_default: bool,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> GroupInfoOut:
    """Create or replace a preset for a group."""
    # get current group
    grp = await get_group(db, group_id)
    presets = grp.presets or {}
    items = []
    default_id = getattr(presets, "default_preset_id", None)

    # convert to mutable structure
    items = [p.model_dump() for p in getattr(presets, "items", [])]

    # check for existing preset and replace or append
    replaced = False
    for idx, p in enumerate(items):
        if p.get("preset_id") == preset.preset_id:
            items[idx] = preset.model_dump()
            replaced = True
            break
    if not replaced:
        items.append(preset.model_dump())

    new_presets = {"default_preset_id": preset.preset_id if set_default else default_id, "items": items}
    payload = {"presets": new_presets, "modified_at": get_timestamp()}

    event_subject = Subject(id=group_id, type=SourceType.USR)
    with audit_event_context(audit, "upsert_preset", ctx, event_subject):
        try:
            updated = await db.sample_group_collection.find_one_and_update(
                {"group_id": group_id},
                {"$set": payload},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as pme:
            LOG.error("MongoDB error while upserting preset: %s", str(pme))
            raise DatabaseOperationError(
                f"Database error occurred while upserting preset: {str(pme)}"
            ) from pme

        if not updated:
            raise EntryNotFound(group_id)

    return GroupInfoOut.model_validate(updated)


async def delete_preset(
    db: Database,
    group_id: str,
    preset_id: str,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> GroupInfoOut:
    """Delete a preset from a group."""
    grp = await get_group(db, group_id)
    presets = grp.presets
    if not presets or not presets.items:
        raise EntryNotFound(preset_id)

    items = [p.model_dump() for p in presets.items if p.preset_id != preset_id]
    if len(items) == len(presets.items):
        raise EntryNotFound(preset_id)

    # adjust default if it pointed to the removed preset
    default_id = presets.default_preset_id
    if default_id == preset_id:
        default_id = items[0]["preset_id"] if items else None

    new_presets = {"default_preset_id": default_id, "items": items}
    payload = {"presets": new_presets, "modified_at": get_timestamp()}

    event_subject = Subject(id=group_id, type=SourceType.USR)
    with audit_event_context(audit, "delete_preset", ctx, event_subject):
        try:
            updated = await db.sample_group_collection.find_one_and_update(
                {"group_id": group_id},
                {"$set": payload},
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as pme:
            LOG.error("MongoDB error while deleting preset: %s", str(pme))
            raise DatabaseOperationError(
                f"Database error occurred while deleting preset: {str(pme)}"
            ) from pme

        if not updated:
            raise EntryNotFound(group_id)

    return GroupInfoOut.model_validate(updated)
