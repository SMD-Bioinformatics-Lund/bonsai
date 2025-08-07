"""Login page POM."""

import logging

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from .utils import get_test_id_selector

LOG = logging.getLogger(__name__)


class LoginPage:
    """Login page object model."""

    def __init__(self, driver: WebDriver, base_url: str, timeout: int = 10):
        self.driver = driver
        self.timeout: int = timeout
        self.wait: WebDriverWait = WebDriverWait(driver, timeout)
        self.base_url: str = base_url

        self.username_selector = get_test_id_selector("username-input")
        self.password_selector = get_test_id_selector("password-input")
        self.login_btn_selector = get_test_id_selector("login-btn")

    def load(self):
        """Load the login page."""
        self.driver.maximize_window()
        self.driver.get(self.base_url + "/login")
        self.wait.until(EC.element_to_be_clickable(self.username_selector))

    def login(self, username: str, password: str):
        """Login to the application."""

        LOG.warning("URL before login: %s", self.driver.current_url)
        LOG.warning("Logging in with username: %s", username)
        self.wait.until(EC.element_to_be_clickable(self.username_selector))
        self.driver.find_element(*self.username_selector).send_keys(username)

        self.wait.until(EC.element_to_be_clickable(self.password_selector))
        self.driver.find_element(*self.password_selector).send_keys(password)

        self.wait.until(EC.element_to_be_clickable(self.login_btn_selector))
        LOG.warning("Performing loging action")
        self.driver.find_element(*self.login_btn_selector).click()

        self.wait.until(lambda d: d.current_url != self.base_url + "/login")
        LOG.warning("URL after login: %s", self.driver.current_url)
