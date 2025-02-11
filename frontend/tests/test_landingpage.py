"""Test basic landing page functionality."""
from bs4 import BeautifulSoup
from flask_login.test_client import FlaskLoginClient


def test_development_indicator(test_client: FlaskLoginClient):
    """Test that development indicator is displayed when in dev mode."""

    # goto landing page
    response = test_client.get("/")
    dom = BeautifulSoup(response.data, 'html.parser')

    # search for testing alert
    tag = dom.find(id="testing-instance-alert")

    assert tag is not None


def test_development_indicator(client: FlaskLoginClient):
    """Test that development indicator is displayed when in dev mode."""

    # goto landing page
    response = client.get("/")
    dom = BeautifulSoup(response.data, 'html.parser')

    # search for testing alert
    tag = dom.find(id="testing-instance-alert")

    assert tag is None