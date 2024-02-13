"""Test Bonsai CLI commands."""

from app.cli import export
from click.testing import CliRunner


def test_export_sample(sample_database):
    """Test exporting a sample as LIMS import file."""

    runner = CliRunner()
    with runner.isolated_filesystem():
        args = ["export", "-i", "test_mtuberculosis_1"]
        result = runner.invoke(export, args)
        assert result.exit_code == 0
