"""Tests for the /groups view."""
from pathlib import Path
from ..conftest import get_element_by_test_id, get_bootstrap_alert

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def test_samples_are_displayed(logged_in_user, config):
    """Test that login to Bonsai works."""
    # go to groups view
    logged_in_user.get(str(Path(config['frontend_url']) / 'groups'))

    # get sample table
    sample_table = logged_in_user.find_element(By.ID, "sample-table")
    sample_rows = sample_table.find_elements(By.XPATH, "//tbody/tr")

    assert len(sample_rows) > 0


def test_add_samples_to_basket(logged_in_user, config):
    """Test samples can be added to the basket."""
    # go to groups view
    logged_in_user.get(str(Path(config['frontend_url']) / 'groups'))

    # then select the first sample in the table
    get_element_by_test_id(logged_in_user, "sample-row-1").click()

    # then check that the add to basket button has been enabled
    add_to_basket_btn = get_element_by_test_id(logged_in_user, "add-to-basket-btn")
    assert add_to_basket_btn.is_enabled()

    # then click the button
    add_to_basket_btn.click()

    # wait for page to load
    logged_in_user.implicitly_wait(2)

    # verify that no error alerts were thrown
    alert = get_bootstrap_alert(logged_in_user)
    assert alert is None, f"Alert error: {alert.text}"

    # check that the sample has been added to the basket
    get_element_by_test_id(logged_in_user, "samples-in-basket-counter")