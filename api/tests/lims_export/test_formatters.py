"""Test lims export functions."""

import pytest
from bonsai_api.lims_export.formatters import (
    AnalysisNoResultError,
    AnalysisNotPresentError,
    amr_prediction_for_antibiotic,
    lineage_prediction,
    mlst_typing,
    qc_status,
    species_prediction,
)


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
    with pytest.raises(AnalysisNotPresentError):
        species_prediction(sample=ecoli_sample, options={"software": "mykrobe"})


def test_get_species_with_mykrobe_result(mtuberculosis_sample):
    """Test that the formatting function for mykrobe spp results."""
    # test trying to access predictions from a unused software raises an error
    species, comment = species_prediction(
        sample=mtuberculosis_sample, options={"software": "mykrobe"}
    )

    assert species == "Mycobacterium tuberculosis"
    assert comment == ""


def test_get_tbprofiler_lineage(mtuberculosis_sample):
    """Test that the formatting function for mykrobe spp results."""
    # test trying to access predictions from a unused software raises an error
    species, comment = lineage_prediction(sample=mtuberculosis_sample, options={})

    assert species == "2.2.1"
    assert comment == ""


def test_get_qc_status(mtuberculosis_sample):
    """Test that the formatting function for mykrobe spp results."""
    # test trying to access predictions from a unused software raises an error
    species, comment = qc_status(sample=mtuberculosis_sample, options={})

    assert species == "Unprocessed"
    assert comment == ""


def test_get_tbprofiler_amr_all(mtuberculosis_sample):
    """Test that the parsing of resistance variants works."""

    # First see tbprofiler predicted rifampicin resistance
    # Test sample has one "verfied" rif variant
    opts = {
        "software": "tbprofiler",
        "antibiotic_name": "rifampicin",
        "resistance_level": "all",
    }
    species, comment = amr_prediction_for_antibiotic(
        sample=mtuberculosis_sample, options=opts
    )

    assert species == "Rv1129c.c.-28T>C WHO-5"
    assert comment == ""

    # Test that  resistance levels filter work
    # The sample dont carry a resistance with low grade resistance
    opts = {
        "software": "tbprofiler",
        "antibiotic_name": "rifampicin",
        "resistance_level": "low",
    }
    with pytest.raises(AnalysisNoResultError):
        amr_prediction_for_antibiotic(sample=mtuberculosis_sample, options=opts)

    # The sample carry a variant that confers high level resistance
    opts = {
        "software": "tbprofiler",
        "antibiotic_name": "isoniazid",
        "resistance_level": "high",
    }
    species, comment = amr_prediction_for_antibiotic(
        sample=mtuberculosis_sample, options=opts
    )

    assert species == "Rv1129c.c.-28T>C WHO-5"
    assert comment == ""


def test_get_tbprofiler_amr_no_antibiotic(mtuberculosis_sample):
    """Test that the parsing of resistance variants works."""

    # Test that absent resistance returns null
    opts = {"software": "tbprofiler", "antibiotic_name": "not-a-valid-name"}
    with pytest.raises(AnalysisNoResultError):
        amr_prediction_for_antibiotic(sample=mtuberculosis_sample, options=opts)
