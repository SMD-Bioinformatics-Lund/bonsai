"""Test Bonsai CLI commands."""

import pytest
import pandas as pd

from app.cli import export
from app.io import TARGETED_ANTIBIOTICS
from click.testing import CliRunner


@pytest.mark.asyncio()
def test_export_sample(mocker, sample_database):
    """Test exporting a sample as LIMS import file."""

    # patch db before running cli
    mocker.patch("app.cli.db", sample_database)

    # run CLI command
    runner = CliRunner()
    with runner.isolated_filesystem():
        args = ["-i", "test_mtuberculosis_1", "test.tsv"]
        result = runner.invoke(export, args)

        # test that script could execute
        assert result.exit_code == 0

        # test that the output contained one row per antibiotic
        df = pd.read_csv("test.tsv", sep="\t")
        n_antibiotics = sum([
            2 if antib['split_res_level'] else 1 
            for antib in TARGETED_ANTIBIOTICS.values()
        ])
        assert len(df) == n_antibiotics + 2  # + lineage and spp pred