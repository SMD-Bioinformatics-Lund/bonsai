"""Routes related to collections of samples."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .base import ForbidExtraModelMixin, Timestamps, RWModel

FilterParams = list[dict[str, str | int | float],]


class GroupCore(RWModel):  # pylint: disable=too-few-public-methods
    """Basic specie information."""

    group_id: str = Field(..., min_length=5)
    display_name: str = Field(..., min_length=1, max_length=45)
    description: str | None = None
    sample_count: int = Field(default=0, ge=0)


class ColumnOverride(BaseModel):
    """Defines column overrides for group sample table."""

    id: str = Field(..., description="Column id")
    visible: bool | None = None
    sortable: bool | None = None
    searchable: bool | None = None
    order: int | None = None
    locked: bool | None = Field(None, description="If true, user cannot change this column setting")
    width: int | None = None
    label: str | None = Field(None, description="Custom column label")


class GroupPreset(BaseModel):
    """Defines preset column settings for group sample table."""

    preset_id: str
    label: str
    manifest_version: str
    overrides: list[ColumnOverride] = Field(default_factory=list)


class GroupPresets(ForbidExtraModelMixin):
    """Preset collection ofr a group and track the default preset id."""

    default_preset_id: str
    items: list[GroupPreset] = []

    def get(self, preset_id: str) -> GroupPreset | None:
        """Get preset by id."""
        if not self.items:
            return None

        pid = preset_id or self.default_preset_id
        for preset in self.items:
            if preset.preset_id == pid:
                return preset
        return None


class GroupAllowed(ForbidExtraModelMixin):
    """Explicit catalog of columns users can choose from."""

    column_ids: list[str] = []


class GroupRecordDb(Timestamps, ForbidExtraModelMixin):
    """Database representation of a group.
    
    - core: identitiy and description
    - allowed_columns: permitted data columns
    - presets: named column subsets with overrides
    - schema_version: version of the group schema
    """

    schema_version: int = 1
    core: GroupCore
    allowed_columns: GroupAllowed = Field(default_factory=GroupAllowed)
    presets: GroupPresets | None = None


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
