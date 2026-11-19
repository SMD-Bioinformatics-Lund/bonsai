"""User updates return public user data and preserve password handling."""

from types import SimpleNamespace

import pytest
from bonsai_libs.api_client.audit_log.models import Actor, SourceType
from bonsai_libs.api_client.bonsai.models import UserResponse
from mongomock_motor import AsyncMongoMockClient

from bonsai_api.auth import verify_password
from bonsai_api.crud.user import update_user
from bonsai_api.models.context import ApiRequestContext
from bonsai_api.models.user import UserInputCreate, UserInputDatabase


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["none", "profile", "password"])
async def test_update_returns_sdk_readable_user_without_plaintext_password(change):
    collection = AsyncMongoMockClient().test.users
    existing = UserInputDatabase(
        username="testuser",
        first_name="Test",
        last_name="User",
        email="testuser@example.com",
        roles=["user"],
        hashed_password="existing-password-hash",
    )
    await collection.insert_one(existing.model_dump())
    before = await collection.find_one({"username": "testuser"})
    data = existing.model_dump(exclude={"hashed_password", "created_at", "modified_at"})
    data["password"] = "NewPassword123" if change == "password" else ""
    if change == "profile":
        data.update(first_name="Updated", roles=["user", "uploader"])
    user = UserInputCreate(**data)
    context = ApiRequestContext(
        actor=Actor(id="admin", type=SourceType.USR), metadata={}
    )

    result = await update_user(
        SimpleNamespace(user_collection=collection),
        username="testuser",
        user=user,
        ctx=context,
    )

    output = result.model_dump(mode="json")
    sdk_user = UserResponse.model_validate(output)
    assert sdk_user.first_name == user.first_name
    assert sdk_user.roles == user.roles
    assert "password" not in output
    assert "hashed_password" not in output
    stored = await collection.find_one({"username": "testuser"})
    assert "password" not in stored
    if change == "password":
        assert stored["hashed_password"] != existing.hashed_password
        assert verify_password(data["password"], stored["hashed_password"])
    else:
        assert stored["hashed_password"] == existing.hashed_password
    if change == "none":
        assert stored == before
    assert stored["first_name"] == user.first_name
    assert stored["roles"] == user.roles
