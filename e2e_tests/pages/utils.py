import logging

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

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
