import logging
import time

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait

LOG = logging.getLogger(__name__)


def get_test_id_selector(test_id: str) -> tuple[str, str]:
    """Get selector for test id."""
    return By.XPATH, f"//*[@data-test-id='{test_id}']"


def get_element_by_test_id(driver: WebDriver, test_id: str) -> WebElement:
    """Get HTML DOM element with a given test id.

    Args:
        driver (webdriver): Selenium web driver
        test_id (str): id for DOM element

    Raises:
        NoSuchElementException: raised if no element was found.

    Returns:
        WebElement: Returns the element
    """
    selector = get_test_id_selector(test_id)
    try:
        element: WebElement = driver.find_element(*selector)
    except NoSuchElementException:
        raise NoSuchElementException(f"No element with the test id: {test_id}")
    return element


def get_bootstrap_alert(driver: WebDriver, severity: str = "all") -> WebElement | None:
    """Get bootstrap alert."""
    query_class_names = "alert"
    if not severity == "all":
        query_class_names = f"{query_class_names} alert-{severity}"

    # look for alert DOM element
    try:
        element: WebElement = driver.find_element(By.CLASS_NAME, query_class_names)
    except NoSuchElementException:
        LOG.debug("No alert was found!")
        return None
    return element


def reload_page_with_retries(
    driver: WebDriver, url: str, n_tries: int = 5
) -> None | bool:
    """
    Attempts to reload the given URL up to `n_tries` times if the page fails to load (i.e., the URL does not change).

        LOG.info("Retrying page load, attempt %d", i)
        driver (WebDriver): Selenium web driver instance.
        url (str): The URL to load.
        n_tries (int, optional): Number of attempts to reload the page. Defaults to 5.

    Returns:
        bool: True if the URL changed successfully, otherwise raises an Exception.

    Raises:
        Exception: If the URL does not change after all attempts.
    """
    previous_url: str = driver.current_url
    for i in range(n_tries):
        LOG.info("Attempt %d: Navigating to %s from %s", i + 1, url, previous_url)
        driver.get(url)
        try:
            WebDriverWait(driver, 10).until(lambda d: d.current_url != previous_url)
            LOG.info("URL changed to %s", driver.current_url)
            return True
        except TimeoutException:
            LOG.warning("Timeout waiting for URL to change from %s", previous_url)
        time.sleep(1)
    raise NoSuchElementException(f"Failed to chagne the URL after {n_tries} attempts.")
