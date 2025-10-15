"""Groups page object for the e2e tests."""

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC

from .basket_offcanvas import BasketOffcanvas
from .utils import get_test_id_selector, reload_page_with_retries


class BaseGroupPage(BasketOffcanvas):
    """Groups page object model."""

    def __init__(self, driver: WebDriver, base_url: str, timeout: int = 10):
        super().__init__(driver, timeout)
        self.base_url = base_url

        self.sample_table_selector = get_test_id_selector("sample-table")
        self.admin_panel_btn_selector = get_test_id_selector("admin-panel-navbar-btn")
        self.add_to_basket_button_selector = get_test_id_selector("add-to-basket-btn")

    def click_admin_panel(self):
        """Click the admin panel button."""
        admin_panel_btn = self.driver.find_element(*self.admin_panel_btn_selector)
        admin_panel_btn.click()
        self.wait.until(EC.title_contains("Admin Panel"))

    def get_sample_table(self):
        """Get the sample table element."""
        return self.driver.find_element(*self.sample_table_selector)

    def get_samples(self):
        """Get the sample table element."""
        query = '//*[@data-test-id[starts-with(., "sample-row-")]]'
        return self.driver.find_elements(By.XPATH, query)

    def click_sample_row(self, row_index: int):
        """Click a sample row by index."""
        samples = self.get_samples()
        if row_index < len(samples):
            row = samples[row_index]
            # focus view on row for javasscript to work
            actions = ActionChains(self.driver)
            actions.move_to_element(row).perform()
            row.click()
        else:
            raise IndexError("Sample row index out of range.")

    def select_multiple_samples(self, start_index: int, end_index: int):
        """Select multiple samples by range."""
        samples = self.get_samples()
        if start_index < 0 or end_index >= len(samples) or start_index > end_index:
            raise IndexError("Invalid sample row indices for selection.")

        actions = ActionChains(self.driver)
        actions.key_down(Keys.CONTROL)
        for i in range(start_index, end_index + 1):
            actions.click(on_element=samples[i])
        actions.key_up(Keys.CONTROL)
        actions.perform()

    def get_add_to_basket_button(self):
        """Get the add to basket button."""
        return self.driver.find_element(*self.add_to_basket_button_selector)

    def click_add_to_basket(self):
        """Click the add to basket button."""
        self.get_add_to_basket_button().click()
        self.wait.until(EC.visibility_of_element_located(self.basket_counter_selector))

    def click_open_qc_view(self):
        """Click the QC view button."""
        qc_view_btn = self.driver.find_element(
            *get_test_id_selector("open-qc-view-btn")
        )
        qc_view_btn.click()
        self.wait.until(EC.title_contains("QC results"))


class GroupPage(BaseGroupPage):
    """Group page object model."""

    def __init__(
        self, driver: WebDriver, base_url: str, group_path: str, timeout: int = 10
    ):
        super().__init__(driver, base_url, timeout)
        self.group_path = group_path  # e.g. saureus, mtuberculosis etc

    def load(self):
        """Load the groups page."""
        url = f"{self.base_url}/groups/{self.group_path}"
        # self.driver.get(url)
        reload_page_with_retries(self.driver, url)
        self.wait.until(EC.title_contains(f"Group - {self.group_path}"))


class GroupsOverviewPage(BaseGroupPage):
    """Groups overview page object model."""

    def __init__(self, driver: WebDriver, base_url: str, timeout: int = 10):
        super().__init__(driver, base_url, timeout=timeout)
        self.group_path = ""
        self.group_container_selector = get_test_id_selector("group-container")

    def load(self):
        """Load the groups overview page."""
        url = f"{self.base_url}/groups"
        reload_page_with_retries(self.driver, url)
        self.wait.until(EC.visibility_of_element_located(self.group_container_selector))
