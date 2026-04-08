"""Group service layer."""

import logging
from typing import Any

from api_client.audit_log.client import AuditLogClient
from api_client.audit_log.models import SourceType, Subject
from bonsai_api.crud.builder.summary_manifest import MANIFEST, Manifest
from bonsai_api.crud.builder.types import PipelineStages
from bonsai_api.crud.group import (
    delete_group_by_group_id,
    fetch_group_raw,
    find_group_owner_id,
    insert_group_document,
    update_group_core_doc,
    upsert_preset_doc,
)
from bonsai_api.crud.user import user_exists
from bonsai_api.crud.utils import audit_event_context, managed_transaction
from bonsai_api.db import Database
from bonsai_api.exceptions import (
    ConflictError,
    DatabaseOperationError,
    EntryNotFound,
    ForbiddenAccess,
    UserNotFound,
)
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.group import (
    DEFAULT_PRESET_NAME,
    ColumnOut,
    ColumnOverride,
    GroupAllowed,
    GroupCore,
    GroupInfoCreate,
    GroupInfoOut,
    GroupPresetIn,
    GroupPresets,
    GroupRecordDb,
    GroupUpdate,
    Visibility,
)
from bonsai_api.models.user import UserContext
from bonsai_api.utils import get_timestamp
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError, PyMongoError

from .membership_service import get_samples_by_group_ids, remove_memberships

LOG = logging.getLogger(__name__)


def _validate_presets_and_default(
    presets_in: list[GroupPresetIn] | None, default_pid: str | None
) -> None:
    """Validate preset uniqueness and that default pid is present when given."""
    presets_in = presets_in or []
    preset_ids = [p.preset_id for p in presets_in]
    if len(preset_ids) != len(set(preset_ids)):
        raise ValueError("Duplicate preset ids provided in presets")
    if default_pid and default_pid not in preset_ids:
        raise ValueError("default_preset_id must match one of the provided presets")


def _validate_allowed_columns(
    allowed_columns: list[str] | None, *, manifest: Manifest
) -> None:
    """Validate allowed column IDs against the manifest."""
    if allowed_columns is None:
        return
    if not all(isinstance(c, str) for c in allowed_columns):
        raise ValueError("allowed_columns must be a list of strings")
    manifest_column_ids = {col.id for col in manifest.columns}
    for col in allowed_columns:
        if col not in manifest_column_ids:
            raise ValueError(f"Invalid column id in allowed_columns: {col}")


def _build_group_payload(
    group_record: GroupInfoCreate, owner_id: str | None
) -> GroupRecordDb:
    """Build GroupRecordDb representation from create payload."""
    core = GroupCore(
        group_id=group_record.group_id,
        display_name=group_record.display_name,
        description=group_record.description,
        visibility=group_record.visibility,
        owner_id=owner_id,
    )
    presets_obj = GroupPresets(
        default_preset_id=group_record.default_preset_id or DEFAULT_PRESET_NAME,
        items=group_record.presets or [],
    )
    allowed_cols = GroupAllowed(column_ids=group_record.allowed_columns or [])
    return GroupRecordDb(
        core=core,
        invited_users=group_record.invited_users or [],
        allowed_columns=allowed_cols,
        presets=presets_obj,
    )


def _build_group_output(group_record: dict[str, Any] | GroupRecordDb) -> GroupInfoOut:
    """Build group output object from a raw db record."""
    if not isinstance(group_record, GroupRecordDb):
        # Try to cast input data as a group_record
        try:
            group_record.pop("_id", False)  # drop mongo oid
            group_record = GroupRecordDb.model_validate(group_record)
        except ValidationError as exc:
            raise RuntimeError(
                "Failed to cast group_record as GroupRecordDb", exc
            ) from exc

    default_preset = (
        None if group_record.presets is None else group_record.presets.default_preset_id
    )
    return GroupInfoOut(
        group_id=group_record.core.group_id,
        display_name=group_record.core.display_name,
        description=group_record.core.description,
        sample_count=0,
        default_preset_id=default_preset,
    )


async def create_group_service(
    db: Database,
    *,
    group_record: GroupInfoCreate,
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
    # Ensure that the specified owner exists
    if not await user_exists(db, user_id=creator.user_id):
        raise UserNotFound(f"Specified group owner '{creator.user_id}' does not exist.")

    # Validate inputs
    _validate_presets_and_default(group_record.presets, group_record.default_preset_id)
    _validate_allowed_columns(group_record.allowed_columns, manifest=MANIFEST)

    # Policy checks, e.g. only owner or admin may create private group
    if (
        group_record.visibility == Visibility.PRIVATE
        and not creator.user_id
        and not creator.is_admin()
    ):
        raise ForbiddenAccess("Only owner or admin may create a private group")

    if group_record.invited_users and not (creator.owner_id or creator.is_admin()):
        raise ForbiddenAccess("Only owner or admin may invited users on creation")

    # Build database document
    payload = _build_group_payload(group_record, creator.user_id)

    event_subject = Subject(id=group_record.group_id, type=SourceType.USR)
    with audit_event_context(audit, "create_group", ctx, event_subject):
        try:
            await insert_group_document(
                db, doc=payload.model_dump(exclude_none=True), session=session
            )
        except DuplicateKeyError as dke:
            LOG.error("Duplicate key error while creating group: %s", str(dke))
            raise ConflictError(
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

    # Return normalized response
    return _build_group_output(payload)


async def delete_group_service(
    db: Database,
    *,
    group_id: str,
    ctx: ApiRequestContext,
    user: UserContext,
    audit: AuditLogClient | None = None,
    session: Any = None,
) -> int:
    """
    Business-level delete group:
    - Ensures group exists.
    - Enforces policy: only owner or admin may delete.
    - Orchestrates related cleanup (memberships).
    - Deletes via repository (CRUD).
    """
    # Check existence + owner fetch
    owner_id = await find_group_owner_id(db, group_id=group_id, session=session)
    if not owner_id:
        raise EntryNotFound(group_id)

    # Check permission
    if not (user.is_admin() or owner_id == user.user_id):
        raise ForbiddenAccess("Only the group owner or admin can delete this group")

    event_subject = Subject(id=group_id, type=SourceType.USR)
    with audit_event_context(
        audit, "delete_group", ctx, event_subject, metadata={"group_id": group_id}
    ):
        # 3) Orchestrate related cleanup inside transaction if you use one
        async with managed_transaction(db.client) as txn:
            # Remove group from stored memberships (use your existing helpers)
            edges = await get_samples_by_group_ids(
                db=db, group_ids=[group_id], session=txn
            )
            await remove_memberships(edges, db=db, session=txn)

            # 4) Delete the group doc
            try:
                deleted = await delete_group_by_group_id(
                    db, group_id=group_id, session=txn
                )
                if deleted == 0:
                    # Race between existence check and delete
                    raise EntryNotFound(group_id)
                return deleted
            except PyMongoError as pme:
                raise DatabaseOperationError(
                    f"Database error during delete_group: {str(pme)}"
                ) from pme


async def get_group_raw(
    db: Database,
    group_id: str,
    *,
    user: UserContext | None = None,
    session: Any = None,
) -> GroupRecordDb:
    """Return the raw group document from the database."""
    if not group_id or not isinstance(group_id, str):
        raise ValueError(
            f"Invalid group_id: must be a non-empty string, got {group_id}"
        )

    try:
        # No visability checks for admins or if no user provided
        kwargs = {}
        if user is None or user.is_admin():
            kwargs["visibility"] = "admin"
        else:
            kwargs["visibility"] = "user"
            kwargs["user_id"] = user.user_id

        raw = await fetch_group_raw(db, group_id=group_id, session=session, **kwargs)
        if not raw:
            raise EntryNotFound(group_id)
        return GroupRecordDb.model_validate(raw)
    except PyMongoError as pme:
        raise DatabaseOperationError(
            f"Database error occurred while retrieving group {group_id}: {str(pme)}"
        ) from pme
    except ValidationError as vde:
        raise RuntimeError(
            f"Failed to cast group_record as GroupRecordDb: {str(vde)}"
        ) from vde


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
            data_pipeline.append(build_group_visibility_match_stage(user_id))

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


async def build_column_overrides(
    group_obj: GroupRecordDb,
    manifest: Manifest,
    *,
    preset: str | None = None,
    include_invisible: bool = False,
) -> list[ColumnOut]:
    """Build list of availbale columns with group specific overrides applied."""
    override_idx: dict[str, ColumnOverride] = {}
    has_preset = group_obj.presets is not None
    if has_preset:
        if group_preset := group_obj.presets.get(preset):
            override_idx = {col.id: col for col in group_preset.overrides}

    result: list[ColumnOut] = []
    for default_order, man_col in enumerate(manifest.columns, start=1):
        # only include allowed columns if allowed columns have been set.
        if len(group_obj.allowed_columns.column_ids) > 0:
            if man_col.id not in group_obj.allowed_columns.column_ids:
                continue

        ov: ColumnOverride | None = override_idx.get(man_col.id)

        # Mutate with override if available
        label = man_col.label if not (ov and ov.label is not None) else ov.label
        visible = (
            man_col.default_visible
            if not (ov and ov.visible is not None)
            else ov.visible
        )
        sortable = (
            man_col.sortable if not (ov and ov.sortable is not None) else ov.sortable
        )
        searchable = None if not (ov and ov.searchable is not None) else ov.searchable
        locked = False if not (ov and ov.locked is not None) else ov.locked
        eff_order = (
            default_order if not (ov and ov.order is not None) else ov.order
        )  # 0 is respected

        if not include_invisible and not visible:
            continue

        # compute overridden_fields that changed-from-default semantics
        overridden_fields: list[str] = []
        if ov:
            if ov.label is not None and ov.label != man_col.label:
                overridden_fields.append("label")
            if ov.visible is not None and ov.visible != man_col.default_visible:
                overridden_fields.append("visible")
            if ov.sortable is not None and ov.sortable != man_col.sortable:
                overridden_fields.append("sortable")
            if ov.searchable is not None:
                overridden_fields.append("searchable")
            if ov.locked is not None and ov.locked is not False:
                overridden_fields.append("locked")
            if ov.order is not None:
                overridden_fields.append("order")

        result.append(
            ColumnOut(
                id=man_col.id,
                type=man_col.type,
                source=man_col.source,
                default_visible=man_col.default_visible,
                filterable=man_col.filterable,
                sortable=sortable,
                visible=visible,
                searchable=searchable,
                order=eff_order,
                locked=locked,
                label=label,
                overridden_fields=overridden_fields,
            )
        )

    result.sort(key=lambda col: (col.order if col.order is not None else col.id))
    return result


async def update_group_core_info(
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
            updated = await update_group_core_doc(db, group_id=group_id, fields=payload)
        except PyMongoError as pme:
            LOG.error("MongoDB error while updating group core: %s", str(pme))
            raise DatabaseOperationError(
                f"Database error occurred while updating group core: {str(pme)}"
            ) from pme

        if not updated:
            raise EntryNotFound(group_id)

        return _build_group_output(updated)


async def upsert_column_preset(
    db: Database,
    group_id: str,
    preset: GroupPresetIn,
    set_default: bool,
    ctx: ApiRequestContext,
    audit: AuditLogClient | None = None,
) -> GroupInfoOut:
    """Create or replace a preset for a group."""
    # get current group
    grp = await get_group_raw(db, group_id=group_id)

    # convert presets from db to a mutable object
    items = []
    if grp.presets is not None:
        items = [itm.model_dump() for itm in grp.presets.items]

    # check for existing preset and replace or append
    replaced = False
    for idx, p in enumerate(items):
        if p.get("preset_id") == preset.preset_id:
            items[idx] = preset.model_dump()
            replaced = True
            break
    if not replaced:
        items.append(preset.model_dump())

    new_presets = {
        "default_preset_id": (
            preset.preset_id if set_default else grp.presets.default_preset_id
        ),
        "items": items,
    }
    upd_group = grp.model_copy(
        update={"presets": new_presets, "modified_at": get_timestamp()}
    )

    event_subject = Subject(id=group_id, type=SourceType.USR)
    with audit_event_context(audit, "upsert_preset", ctx, event_subject):
        try:
            doc = await upsert_preset_doc(
                db, group_id=group_id, payload=upd_group.model_dump()
            )
        except PyMongoError as pme:
            LOG.error("MongoDB error while upserting preset: %s", str(pme))
            raise DatabaseOperationError(
                f"Database error occurred while upserting preset: {str(pme)}"
            ) from pme

        if not doc:
            raise EntryNotFound(group_id)

    try:
        return _build_group_output(doc)
    except ValidationError as exc:
        LOG.error(
            "Failed to validate pydantic model '%s': %s", GroupInfoOut.__name__, doc
        )
        raise RuntimeError(
            f"Failed to cast document as GroupInfoOut: {str(exc)}"
        ) from exc
