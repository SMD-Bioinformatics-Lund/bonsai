"""Tests for the /groups view."""
from pathlib import Path

import pytest
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from ..conftest import get_bootstrap_alert, get_element_by_test_id


def test_samples_are_displayed(logged_in_user, config):
    """Test that login to Bonsai works."""
    # go to groups view
    logged_in_user.get(str(Path(config["frontend_url"]) / "groups"))

    # get sample table
    sample_table = logged_in_user.find_element(By.ID, "sample-table")
    sample_rows = sample_table.find_elements(By.XPATH, "//tbody/tr")

    assert len(sample_rows) > 0


def test_add_samples_to_basket(logged_in_user, config):
    """Test samples can be added to the basket."""
    # setup wait
    wait = WebDriverWait(logged_in_user, 20)
    # go to groups view
    logged_in_user.get(str(Path(config["frontend_url"]) / "groups"))

    # FIRST ensure that basket has been cleared
    get_element_by_test_id(logged_in_user, "open-basket-btn").click()
    clear_basket_btn = wait.until(
        EC.visibility_of_element_located((By.ID, "clear-basket-btn"))
    )
    clear_basket_btn.click()
    wait.until(
        EC.element_to_be_clickable((By.ID, "close-basket-btn"))
    ).click()

    # THEN select the first sample in the table
    get_element_by_test_id(logged_in_user, "sample-row-1").click()

    # THEN check that the add to basket button has been enabled
    add_to_basket_btn = get_element_by_test_id(logged_in_user, "add-to-basket-btn")
    assert add_to_basket_btn.is_enabled()

    # THEN click the button
    add_to_basket_btn.click()

    # wait for page to load
    logged_in_user.implicitly_wait(2)

    # TEST that no error alerts were thrown
    alert = get_bootstrap_alert(logged_in_user, severity="warning")
    assert alert is None, f"Alert error: {alert.text}"

    # TEST that one sample has been added to the basket
    counter = get_element_by_test_id(logged_in_user, "samples-in-basket-counter")
    assert counter.text == "1"

    # THEN clear the basket again
    get_element_by_test_id(logged_in_user, "open-basket-btn").click()
    clear_basket_btn = wait.until(
        EC.visibility_of_element_located((By.ID, "clear-basket-btn"))
    )
    clear_basket_btn.click()
    get_element_by_test_id(logged_in_user, "close-basket-btn").click()

    # TEST that basket was cleared
    counter = get_element_by_test_id(logged_in_user, "samples-in-basket-counter")
    assert counter.text == ""

    # THEN refresh page to test that the change was commited to the API by ensuring that counter element is not in DOM
    logged_in_user.refresh()
    logged_in_user.implicitly_wait(1)
    with pytest.raises(NoSuchElementException):
        counter = get_element_by_test_id(logged_in_user, "samples-in-basket-counter")
