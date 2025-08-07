"""Test functionality of admin page."""

import logging

import pytest
from pages.groups_page import GroupsOverviewPage
from selenium.common.exceptions import NoSuchElementException

LOG = logging.getLogger(__name__)


def test_admin_console_not_accessable_by_user(logged_in_user, config):
    """Test that the admin console is not accessable by user."""

    groups_page = GroupsOverviewPage(logged_in_user, base_url=config["frontend_url"])

    # FIRST go to groups page
    groups_page.load()

    # TEST that admin panel button is not accessable to a regular user
    with pytest.raises(NoSuchElementException):
        groups_page.click_admin_panel()


def test_admin_console_accessable_by_admin(logged_in_admin, config):
    """Test that the admin console is not accessable by user."""

    groups_page = GroupsOverviewPage(logged_in_admin, base_url=config["frontend_url"])

    # FIRST load groups view
    groups_page.load()

    # THEN click the admin panel button
    groups_page.click_admin_panel()

    # TEST that the admin panel loaded
    assert "Admin Panel" in logged_in_admin.title
