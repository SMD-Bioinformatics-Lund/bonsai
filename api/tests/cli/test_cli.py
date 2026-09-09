"""Test CLI commands."""

from types import SimpleNamespace

from bonsai_api.cli.cli import cli
from bonsai_api.exceptions import ConflictError
from click.testing import CliRunner
from mongomock import DuplicateKeyError


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
        ],
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
        ],
    )

    assert result.exit_code != 0
    assert "already taken" in result.output


def test_create_group_success(monkeypatch):
    """Test creating a group with a service-generated ID."""
    runner = CliRunner()

    async def fake_create_group(group, user_id):
        assert group.display_name == "testgroup"
        assert group.description == "Test group"
        assert user_id == "admin"
        return SimpleNamespace(
            group_id="01234567-89ab-7def-8123-456789abcdef",
            display_name=group.display_name,
        )

    monkeypatch.setattr(
        "bonsai_api.cli.cli.run_create_group",
        fake_create_group,
    )

    result = runner.invoke(
        cli,
        [
            "create-group",
            "--name",
            "testgroup",
            "--description",
            "Test group",
        ],
    )

    assert result.exit_code == 0
    assert (
        'Successfully created the group "testgroup" with ID '
        '"01234567-89ab-7def-8123-456789abcdef"' in result.output
    )


def test_create_group_duplicate(monkeypatch):
    """Test handling a group creation conflict."""
    runner = CliRunner()

    async def fake_create_group(group, user_id):
        raise ConflictError("Group already exists.")

    monkeypatch.setattr(
        "bonsai_api.cli.cli.run_create_group",
        fake_create_group,
    )

    result = runner.invoke(
        cli,
        [
            "create-group",
            "--name",
            "testgroup",
            "--description",
            "Test group",
        ],
    )

    assert result.exit_code != 0
    assert 'Error: Group already exists.' in result.output
