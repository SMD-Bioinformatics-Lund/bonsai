"""General record administration regressions from the release UI pass."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from bonsai_libs.api_client.audit_log.models import Actor, SourceType
from bonsai_api.crud import metadata as metadata_crud, user as user_crud
from bonsai_api.crud.memberships import find_samples_by_group_ids
from bonsai_api.crud.group import get_group, get_groups_crud
from bonsai_api.exceptions import EntryNotFound
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.group import GroupInfoCreate
from bonsai_api.models.metadata import GenericMetadataEntry, InputTableMetadata
from bonsai_api.models.sample import SampleRecordDb, SampleRecordOut
from bonsai_api.models.user import UserContext, UserInputCreate, UserInputDatabase
from bonsai_api.services import group_service
from mongomock import MongoClient


def context():
    return ApiRequestContext(actor=Actor(id="owner", type=SourceType.USR), metadata={})


@pytest.mark.asyncio
async def test_group_lookup_does_not_return_a_members_other_groups():
    collection = MongoClient().test.sample
    collection.insert_many([
        {"sample_id": "one", "groups": ["target", "unrelated"]},
        {"sample_id": "two", "groups": ["unrelated"]},
        {"sample_id": "three", "groups": ["target"]},
    ])
    aggregate = AsyncMock(side_effect=lambda pipeline, **kwargs: SimpleNamespace(
        to_list=AsyncMock(return_value=list(collection.aggregate(pipeline)))))
    db = SimpleNamespace(sample_collection=SimpleNamespace(aggregate=aggregate))
    result = await find_samples_by_group_ids(db, group_ids=["target"])
    assert {(x["sample_id"], x["group_id"]) for x in result} == {("one", "target"), ("three", "target")}


@pytest.mark.parametrize("username,can_read", [("owner", True), ("invitee", True), ("outsider", False)])
@pytest.mark.asyncio
async def test_private_group_list_and_direct_access_agree(username, can_read):
    collection = MongoClient().test.sample_group
    collection.insert_one({"core": {"group_id": "private", "group_key": "private", "display_name": "Private",
        "sample_count": 0, "visibility": "private", "owner_id": "owner"}, "invited_users": ["invitee"]})
    aggregate = AsyncMock(side_effect=lambda pipeline, **kwargs: SimpleNamespace(
        to_list=AsyncMock(return_value=list(collection.aggregate(pipeline)))))
    db = SimpleNamespace(sample_group_collection=SimpleNamespace(aggregate=aggregate))
    listed, count = await get_groups_crud(db, user_id=username, user_roles=["user"])
    assert bool(listed) == can_read
    assert count == int(can_read)
    if can_read:
        assert (await get_group(db, "private", user_id=username, user_roles=["user"])).group_id == "private"
    else:
        with pytest.raises(EntryNotFound):
            await get_group(db, "private", user_id=username, user_roles=["user"])


@pytest.mark.parametrize("model", [SampleRecordDb, SampleRecordOut])
def test_stored_metadata_reads_legacy_csv_and_structured_tables(model):
    raw = {"sample_id": "record-1", "external_sample_id": "external-1", "sample_name": "Pending",
           "metadata": [{"fieldname": "Inventory", "category": "general", "type": "table",
                         "value": "Item,Count\nDesk,2\nChair,3\n"}]}
    first = model.model_validate(raw)
    assert first.metadata[0].columns == ["Item", "Count"]
    assert first.metadata[0].data == [["Desk", 2], ["Chair", 3]]
    assert model.model_validate(first.model_dump()).metadata[0].data == first.metadata[0].data


@pytest.mark.asyncio
async def test_appending_metadata_retains_existing_fields_and_normalizes_tables(monkeypatch):
    sample = {"metadata": [{"fieldname": "First", "category": "general", "type": "string", "value": "Retain"}]}
    monkeypatch.setattr(metadata_crud, "get_sample_by_id", AsyncMock(return_value=sample))
    update = AsyncMock(return_value=SimpleNamespace(matched_count=1, modified_count=1))
    db = SimpleNamespace(sample_collection=SimpleNamespace(update_one=update))
    assert await metadata_crud.add_metadata_to_sample("record-1", [
        GenericMetadataEntry(fieldname="Count", category="general", type="integer", value=7),
        InputTableMetadata(fieldname="Inventory", value="Item,Count\nDesk,2\n"),
    ], db)
    stored = update.call_args.args[1]["$set"]["metadata"]
    assert [entry["fieldname"] for entry in stored] == ["First", "Count", "Inventory"]
    assert stored[0]["value"] == "Retain"
    assert stored[2]["columns"] == ["Item", "Count"]
    assert stored[2]["data"] == [["Desk", 2]]


@pytest.mark.asyncio
async def test_duplicate_metadata_has_a_conflict_without_any_write(monkeypatch):
    monkeypatch.setattr(metadata_crud, "get_sample_by_id", AsyncMock(return_value={"metadata": [
        {"fieldname": "First", "category": "general", "type": "string", "value": "Retain"}]}))
    update = AsyncMock()
    db = SimpleNamespace(sample_collection=SimpleNamespace(update_one=update))
    with pytest.raises(FileExistsError, match="First"):
        await metadata_crud.add_metadata_to_sample("record-1", [
            GenericMetadataEntry(fieldname="First", category="general", type="string", value="Replace")], db)
    update.assert_not_awaited()


@pytest.mark.asyncio
async def test_private_group_with_invites_uses_authenticated_owner(monkeypatch):
    monkeypatch.setattr(group_service, "user_exists", AsyncMock(return_value=True))
    insert = AsyncMock()
    monkeypatch.setattr(group_service, "insert_group_document", insert)
    result = await group_service.create_group_service(
        SimpleNamespace(), group_record=GroupInfoCreate(group_key="private_test", display_name="Private",
        visibility="private", invited_users=["invitee"]), ctx=context(),
        creator=UserContext(user_id="owner", roles=["user"]))
    assert result.display_name == "Private"
    assert insert.call_args.kwargs["doc"]["core"]["owner_id"] == "owner"
    assert insert.call_args.kwargs["doc"]["invited_users"] == ["invitee"]


@pytest.mark.asyncio
async def test_profile_update_returns_user_and_preserves_password_hash(monkeypatch):
    old = UserInputDatabase(username="test_user", first_name="Before", email="user@example.org",
                            roles=["user"], hashed_password="existing-hash")
    monkeypatch.setattr(user_crud, "get_user", AsyncMock(return_value=old))
    replace = AsyncMock(return_value=SimpleNamespace(matched_count=1, modified_count=1))
    db = SimpleNamespace(user_collection=SimpleNamespace(replace_one=replace))
    result = await user_crud.update_user(db, "test_user", UserInputCreate(username="test_user",
        first_name="After", email="user@example.org", roles=["user"], password=""), context())
    assert result.first_name == "After"
    stored = replace.call_args.args[1]
    assert stored["hashed_password"] == "existing-hash"
    assert "password" not in stored
    assert "hashed_password" not in result.model_dump()
