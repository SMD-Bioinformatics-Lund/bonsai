"""Test basic Bonsai functionality."""
from pathlib import Path
from urllib.parse import urlparse

from ..conftest import get_element_by_test_id, get_bootstrap_alert


def test_accessable_landingpage(remote_driver, config):
    """Test that Bonsai landingpage is accessable."""
    remote_driver.get(config['frontend_url'])

    # check that welcome message are in the title
    assert "bonsai" in remote_driver.title.lower() 


def test_login_admin(logged_in_admin):
    """Test that login to Bonsai works."""
    # Ensure that login worked
    alert = get_bootstrap_alert(logged_in_admin)

    # Check that no bootstrap alert was thrown
    assert alert is None

    # Check that login was redirected to groups view
    assert urlparse(logged_in_admin.current_url).path == '/groups'


def test_log_out_user(logged_in_admin, config):
    """Test that login out from Bonsai works."""

    # logout user
    # 1. open dropdown
    get_element_by_test_id(logged_in_admin, 'user-options-dropdown').click()
    # 2. click logout button
    get_element_by_test_id(logged_in_admin, 'logout-user-btn').click()

    # Check that no bootstrap alert was thrown
    alert = get_bootstrap_alert(logged_in_admin)
    assert alert is None

    # Check that login was redirected to the landing page
    assert urlparse(logged_in_admin.current_url).path == '/'

    # Ensure that a restricted view is non-accessable
    get_element_by_test_id(logged_in_admin, 'groups-view-btn').click()
    assert urlparse(logged_in_admin.current_url).path == '/login'
