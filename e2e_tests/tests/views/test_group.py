"""Test functions related to sample groups."""

import pytest
from pages.groups_page import GroupPage


@pytest.mark.parametrize("group_id", ["mtuberculosis", "saureus", "ecoli"])
def test_open_group_view(logged_in_user, config, group_id: str):
    """Test that the test groups are working."""

    # FIRST goto the group view
    group_page = GroupPage(
        logged_in_user, base_url=config["frontend_url"], group_path=group_id
    )
    group_page.load()

    # TEST that the page could load
    assert "bonsai" in logged_in_user.title.lower()


@pytest.mark.parametrize("group_id", ["mtuberculosis", "saureus"])
def test_open_qc_view(logged_in_user, config, group_id: str):
    """Test the QC view could be opended for the different test groups."""

    # FIRST goto the group view
    group_page = GroupPage(
        logged_in_user, base_url=config["frontend_url"], group_path=group_id
    )
    group_page.load()

    # THEN click the QC view button
    group_page.click_open_qc_view()

    # TEST that the page could load
    assert "QC results" in logged_in_user.title


@pytest.mark.parametrize("group_id", ["mtuberculosis", "saureus"])
def test_add_samples_to_basket(logged_in_user, config, group_id: str):
    """Test the QC view could be opended for the different test groups."""

    # FIRST goto the group view
    group_page = GroupPage(
        logged_in_user, base_url=config["frontend_url"], group_path=group_id
    )
    group_page.load()

    # Ensure basket is empty
    group_page.clear_basket_if_needed()
    assert group_page.get_basket_count() == 0

    # Select the first sample and add to basket
    group_page.click_sample_row(0)
    btn = group_page.get_add_to_basket_button()
    assert btn.is_enabled()
    group_page.click_add_to_basket()
    assert group_page.get_basket_count() == 1

    # Clear the basket and check it's empty
    group_page.clear_basket_if_needed()
    assert group_page.get_basket_count() == 0
