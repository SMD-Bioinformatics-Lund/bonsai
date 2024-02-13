"""Files used for tests."""

from pathlib import Path

import pytest


@pytest.fixture()
def data_path():
    """Get path of this file"""
    conftest_path = Path(__file__)
    return conftest_path.parent


@pytest.fixture()
def mtuberculosis_sample_path(data_path):
    """Get path for M. tuberculosis sample file"""
    return str(data_path.joinpath("test_mtuberculosis_1.json"))


@pytest.fixture()
def ecoli_sample_path(data_path):
    """Get path for E.coli sample file"""
    return str(data_path.joinpath("test_ecoli_1.json"))
