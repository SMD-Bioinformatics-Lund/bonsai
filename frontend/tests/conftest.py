import pytest
from flask_login import FlaskLoginClient

from bonsai_app.app import create_app
from bonsai_app.blueprints.login.views import LoginUser
from bonsai_app.bonsai import TokenObject


@pytest.fixture()
def app():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
        }
    )

    # other setup can go here
    app.test_client_class = FlaskLoginClient

    yield app

    # clean up / reset resources here


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


#############################################################
##################### User fixtures #########################
#############################################################


@pytest.fixture(scope="function")
def parsed_user():
    """Return user info"""
    user_info = {
        "username": "admin",
        "first_name": "Nollan",
        "last_name": "Nollsson",
        "email": "nollan.nollsson@placeholder.com",
        "roles": ["admin"],
        "created_at": "2023-10-16T12:40:37.239000",
    }
    return user_info


@pytest.fixture(scope="function")
def user_obj(parsed_user):
    """Return a User object"""

    token_obj = TokenObject(token="secret-token", type="Bearer")
    user_obj = LoginUser(parsed_user, token_obj)
    return user_obj
