"""Test base lims export module."""

from bonsai_api.lims_export.export import _to_str


def test_to_str():
    """Test the string formatting function"""

    # test format of missing values
    assert _to_str(None) == "-"
    assert _to_str("") == "-"

    # test that strings are preserved
    assert _to_str("foo") == "foo"

    # test that number conversions
    assert _to_str(1234) == "1234"