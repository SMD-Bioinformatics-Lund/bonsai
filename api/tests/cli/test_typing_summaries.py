"""The typing backfill exposes a dry run and reports concurrent changes."""

from importlib import import_module

import pytest
from click.testing import CliRunner


@pytest.mark.parametrize("dry_run", [False, True])
def test_backfill_cli(monkeypatch, dry_run):
    module = import_module("bonsai_api.cli.cli")

    async def run_backfill(**kwargs):
        assert kwargs == {"dry_run": dry_run}
        return {"pending": 2, "updated": 0 if dry_run else 2, "conflicts": 0}

    monkeypatch.setattr(module, "run_backfill_typing_summaries", run_backfill)
    result = CliRunner().invoke(
        module.cli, ["backfill-typing-summaries"] + (["--dry-run"] if dry_run else [])
    )
    assert result.exit_code == 0
    assert (
        "2 STX typing results would be updated."
        if dry_run
        else "Updated 2 STX typing results."
    ) in result.output


def test_backfill_cli_reports_concurrent_changes(monkeypatch):
    module = import_module("bonsai_api.cli.cli")

    async def run_backfill(**_):
        return {"pending": 2, "updated": 1, "conflicts": 1}

    monkeypatch.setattr(module, "run_backfill_typing_summaries", run_backfill)
    result = CliRunner().invoke(module.cli, ["backfill-typing-summaries"])
    assert result.exit_code == 1
    assert "1 entries changed concurrently" in result.output
