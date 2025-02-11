"""Test functions related to sample groups."""

import pytest
from pathlib import Path
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait

from ..conftest import get_bootstrap_alert, get_element_by_test_id


@pytest.mark.parametrize("group_id", ["mtuberculosis", "saureus", "ecoli"])
def test_open_group_view(logged_in_user, config, group_id: str):
    """Test that the test groups are working."""

    # FIRST goto the group view
    url = Path(config["frontend_url"]) / 'groups' / group_id
    logged_in_user.get(str(url))

    # TEST that the page could load
    assert "bonsai" in logged_in_user.title.lower()


@pytest.mark.parametrize("group_id", ["mtuberculosis", "saureus"])
def test_open_qc_view(logged_in_user, config, group_id: str):
    """Test the QC view could be opended for the different test groups."""

    # FIRST goto the group view
    url = Path(config["frontend_url"]) / 'groups' / group_id
    logged_in_user.get(str(url))

    # THEN click the QC view button
    get_element_by_test_id(logged_in_user, "open-qc-view-btn").click()

    # TEST that the page could load
    assert "bonsai" in logged_in_user.title.lower()


@pytest.mark.parametrize("group_id", ["mtuberculosis", "saureus"])
def test_add_samples_to_basket(logged_in_user, config, group_id: str):
    """Test the QC view could be opended for the different test groups."""

    # setup wait
    wait = WebDriverWait(logged_in_user, 10)

    # FIRST goto the group view
    url = Path(config["frontend_url"]) / 'groups' / group_id
    logged_in_user.get(str(url))

    # THEN ensure that basket has been cleared
    get_element_by_test_id(logged_in_user, "open-basket-btn").click()
    clear_basket_btn = wait.until(
        EC.visibility_of_element_located((By.ID, "clear-basket-btn"))
    )
    clear_basket_btn.click()
    get_element_by_test_id(logged_in_user, "close-basket-btn").click()

    # THEN select the first five samples
    (
        ActionChains(logged_in_user)
        .key_down(Keys.CONTROL)  # hold controll
        .click(on_element = get_element_by_test_id(logged_in_user, f"sample-row-1"))  # select multiple samples
        .click(on_element = get_element_by_test_id(logged_in_user, f"sample-row-2"))
        .click(on_element = get_element_by_test_id(logged_in_user, f"sample-row-3"))
        .click(on_element = get_element_by_test_id(logged_in_user, f"sample-row-4"))
        .click(on_element = get_element_by_test_id(logged_in_user, f"sample-row-5"))
        .key_up(Keys.CONTROL)
    ).perform()
    
    # THEN check that the add to basket button has been enabled
    add_to_basket_btn = get_element_by_test_id(logged_in_user, "add-to-basket-btn")
    assert add_to_basket_btn.is_enabled()

    # THEN click the button
    add_to_basket_btn.click()

    # wait for page to load
    logged_in_user.implicitly_wait(2)

    # TEST that no error alerts were thrown
    alert = get_bootstrap_alert(logged_in_user)
    assert alert is None, f"Alert error: {alert.text}"

    # TEST that one sample has been added to the basket
    counter = get_element_by_test_id(logged_in_user, "samples-in-basket-counter")
    assert counter.text == "5"


def test_empty_group_is_empty(logged_in_user, config):
    """Test that no samples are being displayed in an empty group."""
    # go to the ecoli group view
    logged_in_user.get(str(Path(config["frontend_url"]) / "groups" / "ecoli"))

    # verify that no samples are being displayed in the table
    samples_counter = logged_in_user.find_element(By.ID, "samples-counter")
    assert int(samples_counter.text) == 0

    # get sample table
    sample_table = logged_in_user.find_element(By.ID, "sample-table")

    # verify that the number of samples in the group is 0
    assert sample_table.text.startswith('No data available')