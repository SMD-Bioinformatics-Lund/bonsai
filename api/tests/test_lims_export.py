"""Test lims export functions."""

import pytest

from bonsai_api.lims_export.formatters import mlst_typing, species_prediction

def test_get_mlst_with_result(ecoli_sample):
    """Test that MLST format function extract correct information."""

    st, comment = mlst_typing(sample=ecoli_sample, options={})

    assert st == 58
    assert comment == ""


@pytest.mark.parametrize("fixture_name,exp_spp", [["ecoli_sample", "Escherichia coli"]])
def test_get_species_with_bracken_result(fixture_name, exp_spp, request):
    """Test that ."""
    sample = request.getfixturevalue(fixture_name)
    species, comment = species_prediction(sample=sample, options={})

    assert species == exp_spp
    assert comment == ""


def test_get_species_without_mykrobe_result(ecoli_sample):
    """Test that trying to get a missing result raises error."""
    with pytest.raises(ValueError):
        species_prediction(sample=ecoli_sample, options={"software": "mykrobe"})


def test_get_species_with_mykrobe_result(mtuberculosis_sample):
    """Test that the formatting function for mykrobe spp results."""
    # test trying to access predictions from a unused software raises an error
    species, comment = species_prediction(sample=mtuberculosis_sample, options={"software": "mykrobe"})

    assert species == "Mycobacterium tuberculosis"
    assert comment == ""