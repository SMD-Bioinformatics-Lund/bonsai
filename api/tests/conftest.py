import json
import stat
import textwrap

import pytest
from bonsai_api.crud.user import oauth2_scheme
from bonsai_api.dependencies import get_database
from bonsai_api.main import app
from bonsai_api.models.sample import SampleInDatabase
from fastapi.testclient import TestClient

from .data import *

DATABASE = "testdb"


@pytest.fixture(scope="function")
def mtuberculosis_sample(mtuberculosis_sample_path):
    """Sample db object."""
    with open(mtuberculosis_sample_path) as inpt:
        sample_obj = SampleInDatabase(**json.load(inpt))
    return sample_obj


@pytest.fixture(scope="function")
def ecoli_sample(ecoli_sample_path):
    """Sample db object."""
    with open(ecoli_sample_path) as inpt:
        sample_obj = SampleInDatabase(**json.load(inpt))
    return sample_obj


@pytest.fixture(scope="function")
def lims_rs_export_cnf():
    """Sample db object."""
    return {"streptococcus": {"fields": []}}


@pytest.fixture()
def fastapi_client(sample_database):
    """Setup API test client."""
    # disable authentication for test client
    app.dependency_overrides[oauth2_scheme] = lambda: ""

    # use mocked mongo database
    app.dependency_overrides[get_database] = lambda: sample_database

    client = TestClient(app)

    return client


@pytest.fixture
def valid_qc_threshold_toml() -> str:
    return textwrap.dedent(
        """
        [species.bracken.staphylococcus_aureus]
        min_fraction = 0.6
        min_reads = 10000

        [species.bracken.default]
        min_fraction = 0.5
        min_reads = 5000

        [species.mykrobe.mycobacterium_tuberculosis]
        min_species_coverage = 0.9
        min_phylogenetic_group_coverage = 0.9

        [species.mykrobe.default]
        min_species_coverage = 0.8
        min_phylogenetic_group_coverage = 0.8
    """
    )


@pytest.fixture
def thresholds_file(tmp_path: Path, valid_qc_threshold_toml: str):
    path = tmp_path / "thresholds.toml"
    path.write_text(valid_qc_threshold_toml, encoding="utf-8")
    # secure permissions by default
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return path
