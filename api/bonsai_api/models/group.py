"""Routes related to collections of samples."""

from enum import StrEnum
from typing import Any

from bonsai_api.utils import get_timestamp
from pydantic import BaseModel, Field

from .base import (ForbidExtraModelMixin, MultipleRecordsResponseModel,
                   RWModel, Timestamps)

FilterParams = list[dict[str, str | int | float],]


class Visibility(StrEnum):
    """Group visibility levels."""

    PUBLIC = "public"
    PRIVATE = "private"


class GroupCore(RWModel):  # pylint: disable=too-few-public-methods
    """Basic group core information."""

    group_id: str = Field(..., min_length=5)
    display_name: str = Field(..., min_length=1, max_length=45)
    description: str | None = None
    sample_count: int = Field(default=0, ge=0)
    owner_id: str | None = None
    visibility: Visibility = Field(default=Visibility.PUBLIC)


class ColumnOverride(BaseModel):
    """Defines column overrides for group sample table."""

    id: str = Field(..., description="Column id")
    visible: bool | None = None
    sortable: bool | None = None
    searchable: bool | None = None
    order: int | None = None
    locked: bool | None = Field(
        None, description="If true, user cannot change this column setting"
    )
    width: int | None = None
    label: str | None = Field(None, description="Custom column label")


class GroupPreset(BaseModel):
    """Defines preset column settings for group sample table."""

    preset_id: str
    label: str
    manifest_version: str
    overrides: list[ColumnOverride] = Field(default_factory=list)


class GroupPresets(ForbidExtraModelMixin):
    """Preset collection for a group and track the default preset id."""

    default_preset_id: str | None = None
    items: list[GroupPreset] = Field(default_factory=list)

    def get(self, preset_id: str | None) -> GroupPreset | None:
        """Get preset by id or default."""
        if not self.items:
            return None

        pid = preset_id or self.default_preset_id
        if not pid:
            return None

        for preset in self.items:
            if preset.preset_id == pid:
                return preset
        return None


class GroupAllowed(ForbidExtraModelMixin):
    """Explicit catalog of columns users can choose from."""

    column_ids: list[str] = Field(default_factory=list)


class GroupRecordDb(Timestamps, ForbidExtraModelMixin):
    """Database representation of a group.

    - schema_version: version of the group schema
    - core: identity and description
    - allowed_columns: permitted data columns
    - presets: named column subsets with overrides
    - invited_users: optional list of user ids invited to access private group
    """

    schema_version: int = 1
    core: GroupCore
    allowed_columns: GroupAllowed = Field(default_factory=GroupAllowed)
    presets: GroupPresets | None = None
    invited_users: list[str] = Field(default_factory=list)


class GroupInfoOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Defines output structure of group info."""

    group_id: str
    display_name: str
    description: str | None = None
    sample_count: int

    default_preset_id: str | None = None
    presets: list[dict[str, Any]] = []

    table_columns: list[str] = Field(
        default=[], description="IDs of columns to display."
    )


class GroupAllowedUpdate(BaseModel):
    """Payload to update allowed columns for a group."""

    column_ids: list[str] = Field(default_factory=list)


class GroupPresetIn(BaseModel):
    """Payload to create or replace a preset for a group."""

    preset_id: str
    label: str
    manifest_version: str
    overrides: list[ColumnOverride] = Field(default_factory=list)


class GroupPresetUpdate(BaseModel):
    """Payload to partially update a preset."""

    label: str | None = None
    manifest_version: str | None = None
    overrides: list[ColumnOverride] | None = None


class GroupUpdate(BaseModel):
    """Payload to update mutable group core fields."""

    display_name: str | None = None
    description: str | None = None


class GroupFavorite(RWModel):
    """Represents a user's favorite group link stored in a separate collection."""

    user_id: str
    group_id: str
    created_at: float = Field(default_factory=get_timestamp)


class GroupListResponse(MultipleRecordsResponseModel):
    """Response model for listing groups."""

    data: list[GroupInfoOut]


class GroupInfoCreate(BaseModel):  # pylint: disable=too-few-public-methods
    """Defines output structure of group info used for creation."""

    group_id: str
    display_name: str
    description: str | None = None
    visibility: Visibility = Visibility.PUBLIC
    invited_users: list[str] = Field(default_factory=list)
    allowed_columns: list[str] = Field(default_factory=list)
    default_preset_id: str | None = None
    presets: list[GroupPresetIn] = Field(default_factory=list)
