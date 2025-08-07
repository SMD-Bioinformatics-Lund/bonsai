"""Tests for the /groups view."""

from pages.groups_page import GroupsOverviewPage


def test_samples_are_displayed(logged_in_user, config):
    """Test that login to Bonsai works."""
    # go to groups view
    groups_page = GroupsOverviewPage(logged_in_user, base_url=config["frontend_url"])
    groups_page.load()

    # get sample table
    samples_in_table = groups_page.get_samples()
    assert len(samples_in_table) > 0


def test_add_samples_to_basket(logged_in_user, config):
    """
    Test that a sample can be added to and removed from the basket.
    """
    groups_page = GroupsOverviewPage(logged_in_user, base_url=config["frontend_url"])
    groups_page.load()

    # Ensure basket is empty
    groups_page.clear_basket_if_needed()
    assert groups_page.get_basket_count() == 0

    # Select the first sample and add to basket
    groups_page.click_sample_row(0)
    btn = groups_page.get_add_to_basket_button()
    assert btn.is_enabled()
    groups_page.click_add_to_basket()
    assert groups_page.get_basket_count() == 1

    # Clear the basket and check it's empty
    groups_page.clear_basket_if_needed()
    assert groups_page.get_basket_count() == 0
