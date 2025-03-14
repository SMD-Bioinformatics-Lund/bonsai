"""Test Bonsai CLI commands."""

import pandas as pd
from bonsai_api.cli.cli import export
from bonsai_api.io import TARGETED_ANTIBIOTICS
from click.testing import CliRunner


def test_export_sample(mocker, sample_database_context):
    """Test exporting a sample as LIMS import file."""

    # patch db before running cli
    mocker.patch("bonsai_api.cli.cli.get_db_connection", lambda: sample_database_context)

    # run CLI command
    runner = CliRunner()
    with runner.isolated_filesystem():
        args = ["-i", "test_mtuberculosis_1", "test.tsv"]
        result = runner.invoke(export, args)

        # test that script could execute
        assert result.exit_code == 0

        # test that the output contained one row per antibiotic
        df = pd.read_csv("test.tsv", sep="\t")
        n_antibiotics = sum(
            [
                2 if antib["split_res_level"] else 1
                for antib in TARGETED_ANTIBIOTICS.values()
            ]
        )
        assert len(df) == n_antibiotics + 3  # + lineage, qc, and spp pred
