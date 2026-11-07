"""Export consumes the current stored result descriptor without legacy fields."""

from types import SimpleNamespace

import pytest
from bonsai_api.lims_export.formatters import AnalysisNoResultError, emm_typing


def test_emm_export_reads_the_current_descriptor():
    sample = SimpleNamespace(sample_name="Stored sample", typing_result=[
        SimpleNamespace(analysis_type="mlst", result=SimpleNamespace(sequence_type=1)),
        SimpleNamespace(analysis_type="emm", result=SimpleNamespace(emmtype="stored-label"))])
    assert emm_typing(sample, options={}) == ("stored-label", "")


def test_emm_export_preserves_an_unavailable_result():
    sample = SimpleNamespace(sample_name="Stored sample", typing_result=[SimpleNamespace(analysis_type="emm", result=None)])
    with pytest.raises(AnalysisNoResultError):
        emm_typing(sample, options={})


@pytest.mark.parametrize("result,expected", [({"emmtype": "stored-label"}, "stored-label"), ({"emmtype": None}, "NA"), ({}, "NA")])
def test_emm_export_reads_an_unhydrated_stored_result(result, expected):
    sample = SimpleNamespace(sample_name="Stored sample", typing_result=[SimpleNamespace(analysis_type="emm", result=result)])
    assert emm_typing(sample, options={}) == (expected, "")
