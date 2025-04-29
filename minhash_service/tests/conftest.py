"""Test files and fixtures."""

from pathlib import Path
import pytest

from minhash_service.config import Settings


@pytest.fixture()
def settings():
    """Set fixture directory etc for testing."""
    sig_dir = Path(__file__).parent.joinpath('data')

    return Settings(signature_dir=sig_dir, index_name="index.all")