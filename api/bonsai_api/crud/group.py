"""Functions for conducting CURD operations on group collection"""

import logging
from typing import Any, Literal

from api_client.audit_log.client import AuditLogClient
from api_client.audit_log.models import SourceType, Subject
from bonsai_api.db import Database
from bonsai_api.exceptions import DatabaseOperationError, EntryNotFound
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.group import (
    GroupAllowedUpdate,
    GroupInfoCreate,
    GroupInfoOut,
    GroupListResponse,
)
from bonsai_api.utils import get_timestamp
from pydantic import ValidationError
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError

from .builder.group import (
    build_public_visibility_match_stage,
    build_user_visibility_match_stage,
    group_project_stage,
)
from .builder.helpers import build_facet_pagination, build_sort_stage
from .builder.types import PipelineStages
from .utils import audit_event_context

LOG = logging.getLogger(__name__)


VisibilityScope = Literal["admin", "user", "public_only"]


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
            data_pipeline.append(build_public_visibility_match_stage(user_id))

        # format the group data
        data_pipeline.append(
            group_project_stage(include_allowed=True, include_presets=True)
        )

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

        agg_cursor = await db.sample_group_collection.aggregate(
            data_pipeline, session=session
        )
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
    return GroupListResponse(
        data=validated,
        records_total=records_total[0]["count"] if records_total else len(validated),
    )


async def fetch_group_raw(
    db: Database,
    *,
    group_id: str,
    visibility: VisibilityScope = "public_only",
    user_id: str | None = None,
    session: Any = None,
) -> dict[str, Any] | None:
    """Return the full database record or None if its not found."""
    if not group_id or not isinstance(group_id, str):
        raise ValueError(
            f"Invalid group_id: must be a non-empty string, got {group_id}"
        )

    pipeline: PipelineStages = [
        {"$match": {"core.group_id": group_id}},
    ]

    if visibility == "user":
        if not user_id:
            # fallback to only show public groups if user_id was not provided.
            LOG.warning(
                "User ID was not set with visibility==%s - only returning public groups",
                visibility,
            )
            pipeline.append(build_public_visibility_match_stage())
        else:
            pipeline.append(build_user_visibility_match_stage(user_id))
    elif visibility == "public_only":
        pipeline.append(build_public_visibility_match_stage())

    # visibility == "admin" → no extra filter
    pipeline.extend(
        [
            {"$limit": 1},
            {"$project": {"_id": 0}},
        ]
    )
    cursor = await db.sample_group_collection.aggregate(pipeline, session=session)
    docs = await cursor.to_list(1)
    return docs[0] if docs else None


async def fetch_group_out_doc(
    db: Database,
    *,
    group_id: str,
    visibility: VisibilityScope = "public_only",
    user_id: str | None = None,
    session: Any = None,
) -> dict[str, Any] | None:
    """Return the group document formatted as GroupInfoOut or None if not found."""

    if not group_id or not isinstance(group_id, str):
        raise ValueError(
            f"Invalid group_id: must be a non-empty string, got {group_id}"
        )

    pipeline: PipelineStages = [
        {"$match": {"core.group_id": group_id}},
    ]

    if visibility == "user":
        if not user_id:
            # fallback to only show public groups if user_id was not provided.
            LOG.warning(
                "User ID was not set with visibility==%s - only returning public groups",
                visibility,
            )
            pipeline.append(build_public_visibility_match_stage())
        else:
            pipeline.append(build_user_visibility_match_stage(user_id))
    elif visibility == "public_only":
        pipeline.append(build_public_visibility_match_stage())

    # visibility == "admin" → no extra filter
    pipeline.extend(
        [
            {"$limit": 1},
            group_project_stage(include_presets=True, include_allowed=True),
        ]
    )
    cursor = await db.sample_group_collection.aggregate(pipeline, session=session)
    docs = await cursor.to_list(1)
    return docs[0] if docs else None


async def get_group(
    db: Database,
    group_id: str,
    *,
    user_id: str | None = None,
    user_roles: list[str] | None = None,
    session: Any = None,
) -> GroupInfoOut:
    """Retrieve a single group by `group_id` with access control.

    - Admins: bypass visibility restrictions.
    - Non-admins: must be public OR owner OR invited (missing visibility treated as public).
    - Returns `GroupInfoOut` or raises `EntryNotFound` (404 semantics).
    """
    if not group_id or not isinstance(group_id, str):
        raise ValueError(
            f"Invalid group_id: must be a non-empty string, got {group_id}"
        )

    try:
        data_pipeline: PipelineStages = [
            {"$match": {"core.group_id": group_id}},
        ]
        if user_id is not None and "admin" not in (user_roles or []):
            # non-admin users only see public groups, or those they own / are invited to
            data_pipeline.append(build_public_visibility_match_stage(user_id))

        # add data fields
        data_pipeline.append(group_project_stage(include_presets=True))

        agg_cursor = await db.sample_group_collection.aggregate(
            data_pipeline, session=session
        )
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
            group_id,
            ve,
        )
        raise


async def find_group_owner_id(
    db: Database, *, group_id: str, session: Any = None
) -> str | None:
    """Return owner_id for a group or None if not found."""
    doc = await db.sample_group_collection.find_one(
        {"core.group_id": group_id},
        {"_id": 0, "core.owner_id": 1},
        session=session,
    )
    if not doc:
        return None
    core = doc.get("core") or {}
    owner_id = core.get("owner_id")
    return owner_id if isinstance(owner_id, str) else None


async def _fetch_group_minimal(
    db: Database, group_id: str, session: Any = None
) -> dict[str, Any] | None:
    """Fetch minimal fields required for access checks.

    Tries both top-level `group_id` and `core.group_id` to remain compatible with older documents.
    """
    q = {"$or": [{"group_id": group_id}, {"core.group_id": group_id}]}
    proj = {
        "_id": 0,
        "core.owner_id": 1,
        "core.visibility": 1,
        "invited_users": 1,
        "group_id": 1,
    }
    return await db.sample_group_collection.find_one(q, proj, session=session)


async def check_group_read_permission(
    db: Database,
    group_id: str,
    user_id: str | None,
    user_roles: list[str] | None = None,
    session: Any = None,
) -> bool:
    """Return True if the given user can read the group, False otherwise.

    Policy: public groups are readable by anyone. Private groups are readable by owner, invited users or admins.
    """
    user_roles = user_roles or []
    doc = await _fetch_group_minimal(db, group_id, session=session)
    if not doc:
        return False

    visibility = (
        doc.get("core", {}).get("visibility") or doc.get("visibility") or "public"
    )
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
    db: Database,
    group_id: str,
    user_id: str | None,
    user_roles: list[str] | None = None,
    session: Any = None,
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


async def insert_group_document(
    db: Database,
    *,
    doc: dict[str, Any],
    session: Any = None,
) -> str:
    """Create a new document in the group collection."""
    LOG.debug("Creating group document", extra={"doc": doc})
    return await db.sample_group_collection.insert_one(doc, session=session)


async def delete_group_by_group_id(
    db: Database, *, group_id: str, session: Any = None
) -> int:
    """Delete a group by its core.group_id. Returns deleted_count."""
    result = await db.sample_group_collection.delete_one(
        {"core.group_id": group_id}, session=session
    )
    return result.deleted_count


async def group_exists(db: Database, *, group_id: str, session: Any = None) -> bool:
    """Return True if a group with id exists."""
    doc = await db.sample_group_collection.find_one(
        {"core.group_id": group_id}, {"_id": 1}, session=session
    )
    return bool(doc)


async def check_groups_exists(
    db: Database, *, group_ids: list[str], session: Any = None
) -> list[str]:
    """Check if group with group_id exists in database.

    Return missing group ids.
    """
    if not group_ids:
        return []

    # Deduplicate and sort input ids for consistent behavior
    input_ids = sorted(set(group_ids))

    cursor = db.sample_group_collection.find(
        {"core.group_id": {"$in": input_ids}},
        {"core.group_id": 1, "_id": 0},
        session=session,
    )
    existing_docs = await cursor.to_list(None)
    existing_ids: set[str] = {gr["core"]["group_id"] for gr in existing_docs}

    missing_ids = set(group_ids) - existing_ids
    if missing_ids:
        LOG.warning("Did not find groups: %s", missing_ids)
    return missing_ids


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


async def update_group_core_doc(
    db: Database,
    *,
    group_id: str,
    fields: dict[str, Any],
    session: Any = None,
) -> dict[str, Any] | None:
    """Update group core fields."""
    LOG.debug("Updating group.core document", extra={"fields": fields})
    return await db.sample_group_collection.find_one_and_update(
        {"core.group_id": group_id},
        {"$set": {f"core.{key}": val for key, val in fields.items()}},
        session=session,
        return_document=ReturnDocument.AFTER,
    )


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


async def upsert_preset_doc(
    db: Database,
    *,
    group_id: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    """Upsert group column presets and returns the updated document."""
    LOG.debug("Updating group.presets", extra={"group_id": group_id, "preset": payload})
    updated = await db.sample_group_collection.find_one_and_update(
        {"core.group_id": group_id},
        {"$set": payload},
        return_document=ReturnDocument.AFTER,
    )
    return updated


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
