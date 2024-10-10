import pytest
from pathlib import Path
import yaml
import logging

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

LOG = logging.getLogger(__name__)

def get_element_by_test_id(driver: webdriver, test_id: str) -> WebElement:
    """Get HTML DOM element with a given test id.

    Args:
        driver (webdriver): Selenium web driver
        test_id (str): id for DOM element

    Raises:
        NoSuchElementException: raised if no element was found.

    Returns:
        WebElement: Returns the element
    """
    try:
        element: WebElement = driver.find_element(By.XPATH, f"//*[@data-test-id='{test_id}']")
    except NoSuchElementException:
        raise NoSuchElementException(f"No element with the test id: {test_id}")
    return element


def get_bootstrap_alert(driver, severity: str = "all") -> WebElement | None:
    """Get bootstrap alert."""
    query_class_names = 'alert'
    if not severity == "all":
        query_class_names = f'{query_class_names} alert-{severity}'

    # look for alert DOM element
    try:
        element: WebElement = driver.find_element(By.CLASS_NAME, query_class_names)
    except NoSuchElementException:
        LOG.debug("No alert was found!")
        return None
    return element


@pytest.fixture(scope='session')
def remote_driver(config) -> webdriver:
    """Setup remote driver."""
    browsers = {
        'chrome': ChromeOptions,
        'firefox': FirefoxOptions,
    }
    # get related driver configuration
    driver_config = browsers.get(config['remote_browser'])
    if driver_config is None:
        raise ValueError('Invalid webdriver configuration')
    with webdriver.Remote(command_executor=config['remote_webdriver'],
                          options=driver_config()) as driver:
        yield driver


@pytest.fixture(scope='session')
def logged_in_admin(remote_driver, config):
    """Logging in to Bonsai using the admin credentials in config.yml."""
    remote_driver.maximize_window()

    # goto login url
    url = Path(config['frontend_url']) / 'login'
    remote_driver.get(str(url))

    # login to bonsai
    # write username
    get_element_by_test_id(remote_driver, 'username-input').send_keys(config['admin_username'])

    # write password
    get_element_by_test_id(remote_driver, 'password-input').send_keys(config['admin_password'])

    # click login button
    get_element_by_test_id(remote_driver, 'login-btn').click()
    return remote_driver


@pytest.fixture(scope='session')
def logged_in_user(remote_driver, config):
    """Logging in to Bonsai using the user credentials in config.yml."""
    remote_driver.maximize_window()

    # goto login url
    url = Path(config['frontend_url']) / 'login'
    remote_driver.get(str(url))

    # login to bonsai
    # write username
    get_element_by_test_id(remote_driver, 'username-input').send_keys(config['user_username'])

    # write password
    get_element_by_test_id(remote_driver, 'password-input').send_keys(config['user_password'])

    # click login button
    get_element_by_test_id(remote_driver, 'login-btn').click()
    return remote_driver


@pytest.fixture(scope='session')
def config():
    """Read config."""
    config_path = Path('.') / 'config.yml'
    with config_path.open() as cnf_file:
        return yaml.safe_load(cnf_file)