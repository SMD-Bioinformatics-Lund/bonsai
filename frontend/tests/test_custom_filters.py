"""Tests for Jinja custom filters."""

import pytest
from bonsai_app.custom_filters import human_readable_large_numbers


@pytest.mark.parametrize(
    "number,decimals,expected",
    [(10000, 2, "10.0 K"), (0, 2, "0"), ("", 2, ""), (None, 2, "-")],
)
def test_human_readable_large_numbers(number, decimals, expected):
    """Test the behaviour of the function test_human_readable_large_numbers."""

    assert human_readable_large_numbers(number=number, decimals=decimals) == expected
