"""Test functions related to sample groups."""

import pytest
from pathlib import Path

from ..conftest import get_element_by_test_id


@pytest.mark.parametrize("group_id", ["mtuberculosis", "saureus", "ecoli"])
def test_open_group_view(logged_in_user, config, group_id: str):
    """Test that the test groups are working."""

    # FIRST goto the group view
    url = Path(config["frontend_url"]) / 'groups' / group_id
    logged_in_user.get(str(url))

    # TEST that the page could load
    assert "bonsai" in logged_in_user.title.lower()


@pytest.mark.parametrize("group_id", ["mtuberculosis", "saureus", "ecoli"])
def test_open_qc_view(logged_in_user, config, group_id: str):
    """Test the QC view could be opended for the different test groups."""

    # FIRST goto the group view
    url = Path(config["frontend_url"]) / 'groups' / group_id
    logged_in_user.get(str(url))

    # THEN click the QC view button
    get_element_by_test_id(logged_in_user, "open-qc-view-btn").click()

    # TEST that the page could load
    assert "bonsai" in logged_in_user.title.lower()