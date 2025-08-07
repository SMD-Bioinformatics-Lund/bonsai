"""POM operations for the sample offcanvas in the basket."""

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from .utils import get_test_id_selector


class BasketOffcanvas:
    """Basket offcanvas page object model."""

    def __init__(self, driver: WebDriver, timeout: int = 10):
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(self.driver, timeout)

        self.basket_offcanvas_selector = get_test_id_selector("basket-offcanvas")
        self.open_basket_btn_selector = get_test_id_selector("open-basket-btn")
        self.close_basket_btn_selector = get_test_id_selector("close-basket-btn")
        self.clear_basket_btn_selector = get_test_id_selector("clear-basket-btn")
        self.basket_counter_selector = get_test_id_selector("samples-in-basket-counter")

    def open_basket(self):
        """Open the basket offcanvas."""
        self.driver.find_element(*self.open_basket_btn_selector).click()
        self.wait.until(
            EC.visibility_of_element_located(self.basket_offcanvas_selector)
        )

    def clear_basket(self):
        """Clear the basket."""
        self.wait.until(EC.element_to_be_clickable(self.clear_basket_btn_selector))
        clear_btn = self.driver.find_element(*self.clear_basket_btn_selector)
        clear_btn.click()

    def close_basket(self):
        """Close the basket offcanvas."""
        self.wait.until(EC.element_to_be_clickable(self.close_basket_btn_selector))
        close_btn = self.driver.find_element(*self.close_basket_btn_selector)
        close_btn.click()
        self.wait.until(
            EC.invisibility_of_element_located(self.basket_offcanvas_selector)
        )

    def get_basket_count(self) -> int:
        """Get the number of samples in the basket."""
        self.wait.until(EC.presence_of_element_located(self.basket_counter_selector))
        counter = self.driver.find_element(*self.basket_counter_selector)
        text = counter.text.strip()
        return int(text) if text.isdigit() else 0

    def clear_basket_if_needed(self):
        """Clear the basket if needed."""
        self.open_basket()
        self.clear_basket()
        self.close_basket()

    def cluster_samples(self, cluster_method: str):
        """Cluster samples in the basket using the specified method."""
        self.open_basket()
        cluster_dropdown_selector = get_test_id_selector("cluster-samples-dropdown-btn")
        # open the dropdown to select clustering method
        self.wait.until(EC.element_to_be_clickable(cluster_dropdown_selector)).click()
        cluster_btn_selector = get_test_id_selector(f"cluster-{cluster_method}-btn")

        # trigger cluster job
        cluster_btn = self.wait.until(EC.element_to_be_clickable(cluster_btn_selector))
        cluster_btn.click()

        self.close_basket()

        # THEN wait for clustering to finish
        self.wait.until(EC.number_of_windows_to_be(2))

    def switch_to_grapetree(self):
        """Switch to the GrapeTree window."""
        # loop through until we find a new window handle
        for window_handle in self.driver.window_handles:
            self.driver.switch_to.window(window_handle)
            if "GrapeTree" in self.driver.title:
                break
