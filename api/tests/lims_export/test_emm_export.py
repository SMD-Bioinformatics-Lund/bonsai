"""EMM export accepts current typed results and raw stored result dictionaries."""

from types import SimpleNamespace

import pytest

from bonsai_api.lims_export.export import lims_rs_formatter
from bonsai_api.lims_export.formatters import AnalysisNoResultError, AnalysisNotPresentError, emm_typing
from bonsai_api.lims_export.models import AssayConfig, DataType, FieldDefinition
from bonsai_libs.parse.models.typing import TypingResultEmm


@pytest.mark.parametrize("typed", [False, True])
def test_export_current_emm_result(typed):
    data = {"emmtype": "emm1.0", "emm_cluster": "A-C3", "cluster_count": 1}
    result = TypingResultEmm(**data) if typed else data
    sample = SimpleNamespace(sample_name="EMM sample", typing_result=[
        SimpleNamespace(analysis_type="emm", result=result),
    ])
    config = AssayConfig(assay="emm-test", fields=[
        FieldDefinition(parameter_name="EMM_TYPE", data_type=DataType.EMM, required=True),
    ])

    rows = lims_rs_formatter(sample, config)

    assert len(rows) == 1
    assert rows[0].parameter_value == "emm1.0"


def test_present_but_null_emm_payload_is_no_result():
    sample = SimpleNamespace(typing_result=[SimpleNamespace(analysis_type="emm", result=None)])
    with pytest.raises(AnalysisNoResultError):
        emm_typing(sample, options={})


def test_missing_emm_analysis_is_reported_as_missing():
    sample = SimpleNamespace(sample_name="No EMM sample", typing_result=[])
    with pytest.raises(AnalysisNotPresentError):
        emm_typing(sample, options={})
