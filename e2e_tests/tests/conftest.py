import logging
from pathlib import Path

import pytest
import yaml
from pages.login_page import LoginPage
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

LOG = logging.getLogger(__name__)


@pytest.fixture()
def remote_driver(config) -> WebDriver:
    """Setup remote driver."""
    browsers = {
        "chrome": ChromeOptions,
        "firefox": FirefoxOptions,
    }
    # get related driver configuration
    driver_config = browsers.get(config["remote_browser"])
    options = driver_config()
    options.add_experimental_option("prefs", config.get("options", {}))
    if driver_config is None:
        raise ValueError("Invalid webdriver configuration")
    with webdriver.Remote(
        command_executor=config["remote_webdriver"], options=options
    ) as driver:
        yield driver


@pytest.fixture()
def login_user(remote_driver: WebDriver, base_url) -> callable:
    def _login(username: str, password: str) -> WebDriver:
        """Login to the application."""
        page = LoginPage(remote_driver, base_url=base_url)
        page.load()
        page.login(username, password)
        return remote_driver

    return _login


@pytest.fixture(scope="function")
def logged_in_admin(login_user, config):
    """Logs in as admin and returns a logged-in Selenium driver instance."""

    driver = login_user(config["admin_username"], config["admin_password"])
    LOG.warning("In login admin fixture, current URL: %s", driver.current_url)
    return driver


@pytest.fixture(scope="function")
def logged_in_user(login_user, config):
    """Logs in to Bonsai as a user and returns a logged-in Selenium driver instance."""

    driver = login_user(config["user_username"], config["user_password"])
    LOG.warning("In login user fixture, current URL: %s", driver.current_url)
    return driver


@pytest.fixture(scope="session")
def config():
    """Read config."""
    config_path = Path(".") / "config.yml"
    with config_path.open() as cnf_file:
        return yaml.safe_load(cnf_file)


@pytest.fixture(scope="session")
def base_url(config):
    """Base URL for the application."""

    return config.get("frontend_url", "http://localhost:8000")
