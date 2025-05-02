"""Test IO functions in the Minhash package."""

import pytest
from minhash_service.config import Settings
from minhash_service.minhash.io import add_signatures_to_index, list_signatures_in_index, remove_signatures_from_index


def test_add_signatures_to_index(settings_tmp_index: Settings):
    """Test that signatures can be added to a index."""
    index_path = settings_tmp_index.signature_dir.joinpath(f"{settings_tmp_index.index_name}.sbt.zip")

    # sanity check that the test has been setup properly
    assert not index_path.exists()

    resp = add_signatures_to_index(sample_ids=["DRR237260"], cnf=settings_tmp_index)
    # verify that it evaluated as true
    assert resp

    # verify that index has been created
    assert index_path.exists()


def test_remove_signatures_from_index(settings_tmp_index: Settings):
    """Test that a signature can be removed from a index."""

    # setup test
    index_path = settings_tmp_index.signature_dir.joinpath(f"{settings_tmp_index.index_name}.sbt.zip")
    resp = add_signatures_to_index(sample_ids=["DRR237260", "DRR237261"], cnf=settings_tmp_index)
    assert resp

    # perform test
    resp = remove_signatures_from_index(sample_ids=["DRR237261"], cnf=settings_tmp_index)
    assert resp


def test_list_signatures_in_index(settings_tmp_index: Settings):
    """Test function for listing signatures in index."""
    # setup test
    resp = add_signatures_to_index(sample_ids=["DRR237260", "DRR237261"], cnf=settings_tmp_index)

    in_index = list_signatures_in_index(cnf=settings_tmp_index)
    exp_sigs = sorted([idx.filename.split("_")[0] for idx in in_index])
    assert exp_sigs == ["DRR237260", "DRR237261"]