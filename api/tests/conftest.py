import json
from contextlib import contextmanager
import os
import stat
import textwrap
from typing import Generator

import pytest
from bonsai_api.crud.sample import create_sample
from bonsai_api.crud.user import oauth2_scheme
from bonsai_api.db import Database, get_db
from bonsai_api.main import app
from bonsai_api.models.sample import PipelineResult, SampleInDatabase
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
from prp.models.species import BrackenSpeciesPrediction, MykrobeSpeciesPrediction

from .data import *

DATABASE = "testdb"


@pytest.fixture()
async def mongo_database():
    """Setup Bonsai database instance."""
    db = Database()
    db.client = AsyncMongoMockClient()
    # setup mock database
    db.setup()

    # load basic fixtures
    await db.user_collection.insert_one(
        {
            "username": "admin",
            "password": "admin",
            "first_name": "Nollan",
            "last_name": "Nollsson",
            "email": "palceholder@email.com",
            "roles": ["admin"],
        }
    )
    return db


@pytest.fixture(scope="function")
def mtuberculosis_sample(mtuberculosis_sample_path):
    """Sample db object."""
    with open(mtuberculosis_sample_path) as inpt:
        sample_obj = SampleInDatabase(**json.load(inpt))
    return sample_obj


@pytest.fixture(scope="function")
async def sample_database(mongo_database, mtuberculosis_sample_path):
    """Returns a database client with loaded test data."""

    # read fixture and add to database
    with open(mtuberculosis_sample_path) as inpt:
        data = PipelineResult(**json.load(inpt))
        # create sample in database
        await create_sample(db=mongo_database, sample=data)
        return mongo_database


@pytest.fixture(scope="function")
@contextmanager
def sample_database_context(sample_database):
    """Returns a database client with loaded test data."""
    yield sample_database


@pytest.fixture()
def fastapi_client(sample_database):
    """Setup API test client."""
    # disable authentication for test client
    app.dependency_overrides[oauth2_scheme] = lambda: ""

    # use mocked mongo database
    app.dependency_overrides[get_db] = lambda: sample_database

    client = TestClient(app)

    return client


@pytest.fixture
def valid_qc_threshold_toml() -> str:
    return textwrap.dedent("""
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
    """)


@pytest.fixture
def thresholds_file(tmp_path: Path, valid_qc_threshold_toml: str):
    path = tmp_path / "thresholds.toml"
    path.write_text(valid_qc_threshold_toml, encoding="utf-8")
    # secure permissions by default
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return path