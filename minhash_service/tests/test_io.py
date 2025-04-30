"""Test IO functions in the Minhash package."""

import pytest
from minhash_service.config import Settings
from minhash_service.minhash.io import add_signatures_to_index


def test_add_signatures_to_index(settings_tmp_index: Settings):
    """Test that signatures can be added to a index."""
    resp = add_signatures_to_index(sample_ids=["DRR237260"], cnf=settings_tmp_index)

    # verify that it evaluated as true
    assert resp