"""Test functionality of admin page."""
from pathlib import Path
import pytest
from selenium.common.exceptions import NoSuchElementException

from ..conftest import get_element_by_test_id

def test_admin_console_not_accessable_by_user(logged_in_user, config):
    """Test that the admin console is not accessable by user."""
    # FIRST go to landing page
    logged_in_user.get(str(Path(config["frontend_url"])))

    # TEST that admin panel button is not accessable to a regular user
    with pytest.raises(NoSuchElementException):
        get_element_by_test_id(logged_in_user, "admin-panel-navbar-btn")


def test_admin_console_accessable_by_admin(logged_in_admin, config):
    """Test that the admin console is not accessable by user."""
    # FIRST go to landing page
    logged_in_admin.get(str(Path(config["frontend_url"])))

    # THEN click the admin panel button
    admin_panel_btn = get_element_by_test_id(logged_in_admin, "admin-panel-navbar-btn")
    admin_panel_btn.click()

    # TEST that the admin panel loaded
    assert "bonsai" in logged_in_admin.title.lower()