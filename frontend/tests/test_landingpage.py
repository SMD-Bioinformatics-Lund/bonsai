"""Test basic landing page functionality."""

from bs4 import BeautifulSoup
from flask_login.test_client import FlaskLoginClient


def test_root_redirects_to_groups(client: FlaskLoginClient):
    """Test that the application root points to the primary Groups view."""
    response = client.get("/")

    assert response.status_code == 302
    assert response.location == "/groups"


def test_development_indicator_is_shown(test_client: FlaskLoginClient):
    """Test that the development indicator is displayed on About in dev mode."""

    # goto about page
    response = test_client.get("/about")
    dom = BeautifulSoup(response.data, "html.parser")

    # search for testing alert
    tag = dom.find(id="testing-instance-alert")

    assert tag is not None


def test_development_indicator_is_hidden(client: FlaskLoginClient):
    """Test that the development indicator is hidden on About outside dev mode."""

    # goto about page
    response = client.get("/about")
    dom = BeautifulSoup(response.data, "html.parser")

    # search for testing alert
    tag = dom.find(id="testing-instance-alert")

    assert tag is None
