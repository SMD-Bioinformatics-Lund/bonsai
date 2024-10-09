import pytest
import os
import yaml
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions


@pytest.fixture(scope='session')
def remote_driver(config):
    """Setup remote driver."""
    browsers = {
        'chrome': ChromeOptions,
        'firefox': FirefoxOptions,
    }
    # get related driver configuration
    driver_config = browsers.get(config['remote_browser'])
    if driver_config is None:
        raise ValueError('Invalid webdriver configuration')
    driver_config['loggingPrefs'] = {'browser': 'ALL'}  # increase logging output
    # Instantiate an instance of Remote WebDriver with the desired capabilities.
    with webdriver.Remote(command_executor=config['remote_webdriver'],
                          desired_capabilities=capabilites) as driver:
        yield driver


@pytest.fixture(scope='session')
def logged_in_driver(remote_driver, config):
    """Logging in to Bonsai using the credentials in config.yml."""
    # login to bonsai
    remote_driver.get(os.path.join(config['scout_url'], 'login'))
    remote_driver.maximize_window()
    # login
    remote_driver.find_element_by_tag_name("input").send_keys(config['username'])
    remote_driver.find_element_by_tag_name("input").send_keys(config['password'])
    remote_driver.find_element_by_css_selector("button[type='submit']").click() # go to next page
    return remote_driver


@pytest.fixture(scope='session')
def config():
    """Read config."""
    with open(os.path.join(os.getcwd(), 'config.yml')) as cnf_file:
        return yaml.safe_load(cnf_file)