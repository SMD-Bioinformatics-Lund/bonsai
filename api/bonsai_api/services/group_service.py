"""Group service layer."""

import logging
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError, PyMongoError

from typing import Any
from bonsai_api.crud.group import insert_group_document
from bonsai_api.crud.utils import audit_event_context, check_user_exists
from bonsai_api.exceptions import ConflictError, DatabaseOperationError, UserNotFound, ForbiddenAccess
from bonsai_api.models.user import UserContext
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.group import GroupInfoOut
from bonsai_api.crud.builder.summary_manifest import Manifest, MANIFEST
from bonsai_api.db import Database
from api_client.audit_log.client import AuditLogClient
from api_client.audit_log.models import SourceType, Subject
from bonsai_api.models.group import (GroupAllowed, GroupCore, GroupInfoCreate, 
                                     GroupInfoOut, GroupPresetIn,
                                     GroupPresets, GroupRecordDb,
                                     Visibility)


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


def _validate_allowed_columns(allowed_columns: list[str] | None, *, manifest: Manifest) -> None:
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
    if not await check_user_exists(db, user_id=creator.user_id):
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
            await insert_group_document(db, doc=payload.model_dump(exclude_none=True), session=session)
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
    return GroupInfoOut(
        group_id=group_record.group_id,
        display_name=group_record.display_name,
        description=group_record.description,
        sample_count=0,
        default_preset_id=group_record.default_preset_id,
    )

async def build_column_overrides(group_obj: GroupInfoOut, manifest: Manifest):
    """Build list of availbale columns with group specific overrides applied."""
    return