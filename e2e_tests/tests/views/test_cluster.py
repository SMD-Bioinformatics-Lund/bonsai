"""Test functions related to sample groups."""

import pytest
from pathlib import Path
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait

from ..conftest import get_element_by_test_id

@pytest.mark.parametrize("cluster_method", ["cgmlst", "mlst", "minhash"])
def test_cluster_samples_from_basket(logged_in_user, config, cluster_method):
    """Test the QC view could be opended for the different test groups."""
    # setup wait
    wait = WebDriverWait(logged_in_user, 10)

    # Store the ID of the original window
    original_window = logged_in_user.current_window_handle

    # Check we don't have other windows open already
    assert len(logged_in_user.window_handles) == 1

    # FIRST goto the group view
    group_id = "saureus"
    url = Path(config["frontend_url"]) / 'groups' / group_id
    logged_in_user.get(str(url))

    # THEN ensure that basket has been cleared
    basket_btn = get_element_by_test_id(logged_in_user, "open-basket-btn")
    basket_btn.click()
    clear_basket_btn = wait.until(
        EC.visibility_of_element_located((By.ID, "clear-basket-btn"))
    )
    clear_basket_btn.click()
    wait.until(
        EC.element_to_be_clickable((By.ID, "clear-basket-btn"))
    ).click()

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
    
    # THEN add samples to basket
    get_element_by_test_id(logged_in_user, "add-to-basket-btn").click()

    # THEN wait for the page reload
    wait.until(
        EC.staleness_of(basket_btn)
    )

    # THEN open the sidebar again and cluster samples
    get_element_by_test_id(logged_in_user, "open-basket-btn").click()
    wait.until(
        EC.element_to_be_clickable((By.ID, "basket-cluster-samples"))
    ).click()
    get_element_by_test_id(logged_in_user, f"cluster-{cluster_method}-btn").click()

    # THEN wait for clustering to finish
    wait.until(
        EC.number_of_windows_to_be(2)
    )

    # THEN loop through until we find a new window handle
    for window_handle in logged_in_user.window_handles:
        if window_handle != original_window:
            logged_in_user.switch_to.window(window_handle)
            break

    # Wait for the new tab to finish loading content
    wait.until(EC.title_contains("GrapeTree"))

    # FINALLY cleanup the test
    logged_in_user.close()  # close the extra tab
    logged_in_user.switch_to.window(original_window)  # switch to original window
    get_element_by_test_id(logged_in_user, "clear-basket-btn").click()  # clear basket
    wait.until(
        EC.element_to_be_clickable((By.ID, "close-basket-btn"))
    ).click()  # close sidebar