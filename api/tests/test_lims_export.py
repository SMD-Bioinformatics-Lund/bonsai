"""Test lims export functions."""

from bonsai_api.lims_export.formatters import get_mlst_typing, get_species_prediction

def test_get_mlst_with_result(ecoli_sample):
    """Test that MLST format function extract correct information."""

    st, comment = get_mlst_typing(ecoli_sample)

    assert st == 58
    assert comment == ""


def test_get_species_with_result(ecoli_sample):
    """Test that MLST format function extract correct information."""

    species, comment = get_species_prediction(ecoli_sample)

    assert species == "Escherichia coli"
    assert comment == ""
