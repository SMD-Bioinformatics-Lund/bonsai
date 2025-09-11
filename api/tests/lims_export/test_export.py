"""Test base lims export module."""

import pytest
from bonsai_api.lims_export.export import (
    _to_str,
    lims_rs_formatter,
    serialize_lims_results,
)
from bonsai_api.lims_export.models import (
    AssayConfig,
    DataType,
    FieldDefinition,
    LimsRsResult,
    LimsValue,
)


def test_to_str():
    """Test the string formatting function"""

    # test format of missing values
    assert _to_str(None) == "-"
    assert _to_str("") == "-"

    # test that strings are preserved
    assert _to_str("foo") == "foo"

    # test that number conversions
    assert _to_str(1234) == "1234"


def test_lims_rs_formatter(mtuberculosis_sample):
    """Test the LIMS export formatter."""

    assay_config = AssayConfig(
        assay="tb-test",
        fields=[
            FieldDefinition(parameter_name="MTBC_QC", data_type="qc", required=True),
            FieldDefinition(
                parameter_name="MTBC_SPP", data_type="species", required=True
            ),
            FieldDefinition(
                parameter_name="MTBC_RIF",
                data_type="amr",
                required=True,
                options={"antibiotic_name": "rifampicin"},
            ),
            FieldDefinition(
                parameter_name="MTBC_ETB",
                data_type="amr",
                required=True,
                options={"antibiotic_name": "ethambutol"},
            ),
        ],
    )
    result = lims_rs_formatter(mtuberculosis_sample, assay_config)

    # TEST that the correct number of result was returned
    assert len(result) == len(assay_config.fields)

    # TEST parameter names are correctly assigned
    assert result[0].parameter_name == assay_config.fields[0].parameter_name


def test_lims_rs_formatter_failures(mtuberculosis_sample):
    """Test that required is propegated"""

    assay_config = AssayConfig(
        assay="tb-test",
        fields=[
            FieldDefinition(
                parameter_name="MTBC_MLST", data_type="mlst", required=False
            ),
        ],
    )
    result = lims_rs_formatter(mtuberculosis_sample, assay_config)

    # test that a missing result is properly reported
    assert len(result) == 1
    assert result[0].comment == "not_present"

    assay_config = AssayConfig(
        assay="tb-test",
        fields=[
            FieldDefinition(
                parameter_name="MTBC_MLST", data_type="mlst", required=True
            ),
        ],
    )
    # Test a missing required analysis raises an error
    with pytest.raises(ValueError):
        result = lims_rs_formatter(mtuberculosis_sample, assay_config)


def test_serialize_lims_result():
    """Test the serialization of LIMS result"""
    results = [
        LimsRsResult(
            sample_id="S1",
            parameter_name="MTBC_QC",
            parameter_value="140,0",
            comment='Needs "review", urgent',
        )
    ]

    expected_header = "sample_id,parameter_name,parameter_value,comment"
    output = serialize_lims_results(results, delimiter="csv")

    assert expected_header in output

    assert '"140,0"' in output  # comma should be quoted
    assert '"Needs ""review"", urgent"' in output  # quotes should be esc
