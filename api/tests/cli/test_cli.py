"""Test CLI commands."""

from types import SimpleNamespace
from click.testing import CliRunner
from mongomock import DuplicateKeyError

from bonsai_api.cli.cli import cli

def test_create_user_success(monkeypatch):
    """Test creating a user successfully."""
    runner = CliRunner()

    async def fake_create_user(user):
        return SimpleNamespace(username=user.username)

    monkeypatch.setattr(
        "bonsai_api.cli.cli.run_create_user",
        fake_create_user,
    )

    result = runner.invoke(
        cli,
        [
            "create-user",
            "--username",
            "testuser",
            "--password",
            "testpass",
            "--email",
            "test@mail.com",
            "--role",
            "user",
        ]
    )

    assert result.exit_code == 0
    assert 'Successfully created the user "testuser"' in result.output


def test_create_user_duplicate(monkeypatch):
    """Test creating a user that already exists."""
    runner = CliRunner()

    async def fake_create_user(user):
        raise DuplicateKeyError("Username already exists.")

    monkeypatch.setattr(
        "bonsai_api.cli.cli.run_create_user",
        fake_create_user,
    )

    result = runner.invoke(
        cli,
        [
            "create-user",
            "--username",
            "testuser",
            "--password",
            "testpass",
            "--email",
            "test@mail.com",
            "--role",
            "user",
        ]
    )

    assert result.exit_code != 0
    assert "already taken" in result.output


def test_create_group_success(monkeypatch):
    """Test creating a user successfully."""
    runner = CliRunner()

    async def fake_create_group(group):
        return SimpleNamespace(group_id=group.group_id)

    monkeypatch.setattr(
        "bonsai_api.cli.cli.run_create_group",
        fake_create_group,
    )

    result = runner.invoke(
        cli,
        [
            "create-group",
            "--id",
            "testgroup",
            "--name",
            "testgroup",
            "--description",
            "Test group",
        ]
    )

    assert result.exit_code == 0
    assert 'Successfully created the group "testgroup"' in result.output


def test_create_group_duplicate(monkeypatch):
    """Test creating a user that already exists."""
    runner = CliRunner()

    async def fake_create_group(group):
        raise DuplicateKeyError("Username already exists.")

    monkeypatch.setattr(
        "bonsai_api.cli.cli.run_create_group",
        fake_create_group,
    )

    result = runner.invoke(
        cli,
        [
            "create-group",
            "--id",
            "testgroup",
            "--name",
            "testgroup",
            "--description",
            "Test group",
        ]
    )

    assert result.exit_code != 0
    assert "already exists" in result.output