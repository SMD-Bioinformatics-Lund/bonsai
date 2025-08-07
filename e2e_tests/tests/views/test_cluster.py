"""Test functions related to sample groups."""

import pytest
from pages.groups_page import GroupPage
from selenium.webdriver.support import expected_conditions as EC


@pytest.mark.parametrize(
    "cluster_method,group_id,timeout",
    [
        ("cgmlst", "saureus", 20),
        ("mlst", "saureus", 20),
        ("minhash", "saureus", 20),
        ("snv", "mtuberculosis", 60),
    ],
)
def test_cluster_samples_from_basket(
    logged_in_user, config, cluster_method, group_id, timeout
):
    """Test the QC view could be opended for the different test groups."""

    # FIRST goto the group view
    group_page = GroupPage(
        logged_in_user,
        base_url=config["frontend_url"],
        group_path=group_id,
        timeout=timeout,
    )
    group_page.load()

    original_window = logged_in_user.current_window_handle

    # Ensure basket is empty
    group_page.clear_basket_if_needed()

    # THEN select the first five samples
    group_page.select_multiple_samples(0, 4)

    # THEN add samples to basket
    group_page.click_add_to_basket()

    # THEN open the sidebar again and cluster samples
    group_page.cluster_samples(cluster_method)
    group_page.switch_to_grapetree()

    # FINALLY cleanup the test
    logged_in_user.close()  # close the extra tab
    logged_in_user.switch_to.window(original_window)  # switch to original window

    group_page.clear_basket_if_needed()
