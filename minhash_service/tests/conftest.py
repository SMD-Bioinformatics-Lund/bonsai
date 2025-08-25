"""Test files and fixtures."""

import shutil
from pathlib import Path

import py
import pytest

from minhash_service.config import Settings


@pytest.fixture()
def settings():
    """Set fixture directory etc for testing."""
    sig_dir = Path(__file__).parent.joinpath("data")

    return Settings(signature_dir=sig_dir, index_name="index.all")


@pytest.fixture()
def settings_tmp_index(tmpdir: py.path.LocalPath):
    """Base setting using a teporary index directory."""
    temp_dir = Path(tmpdir)
    sig_dir = Path(__file__).parent.joinpath("data")
    for sig in sig_dir.glob("*.sig"):
        shutil.copy(sig, temp_dir)

    return Settings(signature_dir=temp_dir, index_name="index.tmp")
