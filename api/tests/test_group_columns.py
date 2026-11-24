"""Group Summary resolves the editor's saved column selection."""

import pytest
from bonsai_api.crud.builder.summary_manifest import MANIFEST
from bonsai_api.models.group import (
    ColumnOverride,
    GroupAllowed,
    GroupCore,
    GroupPreset,
    GroupRecordDb,
)
from bonsai_api.services.group_service import build_column_overrides


@pytest.mark.asyncio
async def test_adding_and_removing_a_default_hidden_column():
    group = GroupRecordDb(
        core=GroupCore(group_id="test-group", group_key="test", display_name="Test"),
        allowed_columns=GroupAllowed(column_ids=["sample_id", "sample_name"]),
    )

    group.allowed_columns.column_ids.append("quast_n50")
    columns = await build_column_overrides(
        group, MANIFEST, preset="default", include_invisible=True
    )
    assert [column.id for column in columns] == ["sample_id", "sample_name", "quast_n50"]
    assert columns[-1].visible is False

    visible_columns = await build_column_overrides(group, MANIFEST, preset="default")
    assert [column.id for column in visible_columns] == ["sample_id", "sample_name"]

    group.allowed_columns.column_ids.remove("quast_n50")
    columns = await build_column_overrides(
        group, MANIFEST, preset="default", include_invisible=True
    )
    assert [column.id for column in columns] == ["sample_id", "sample_name"]


@pytest.mark.asyncio
async def test_explicit_preset_visibility_takes_precedence():
    group = GroupRecordDb(
        core=GroupCore(group_id="test-group", group_key="test", display_name="Test"),
        allowed_columns=GroupAllowed(column_ids=["sample_id", "quast_n50"]),
    )
    group.presets.items.append(
        GroupPreset(
            preset_id="default",
            label="Default",
            overrides=[ColumnOverride(id="quast_n50", visible=True)],
        )
    )

    columns = await build_column_overrides(group, MANIFEST, preset="default")
    assert [column.id for column in columns] == ["sample_id", "quast_n50"]
    assert columns[-1].visible is True
