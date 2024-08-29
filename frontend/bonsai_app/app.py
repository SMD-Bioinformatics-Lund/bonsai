"""Code for setting up the flask app."""

from itertools import zip_longest

from flask import Flask

from .blueprints import admin, alignviewers, api, cluster, groups, login, public, sample
from .config import settings
from .custom_filters import FILTERS as JINJA_FILTERS
from .custom_filters import TESTS as JINJA_TESTS
from .extensions import login_manager


def create_app():
    """Flask app factory function."""
    app = Flask(__name__)

    # load default config from pydantic settings
    app.config.update(
        {name.upper(): val for name, val in settings.model_dump().items()}
    )

    # initialize flask extensions
    login_manager.init_app(app)

    # import jinja2 extensions
    app.jinja_env.add_extension("jinja2.ext.do")
    app.jinja_env.globals.update(zip_longest=zip_longest)

    # whitespace control:
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    # configure pages etc
    register_blueprints(app)
    register_filters(app)
    register_tests(app)

    return app


def register_blueprints(app):
    """Register flask blueprints."""
    app.register_blueprint(public.public_bp)
    app.register_blueprint(login.login_bp)
    app.register_blueprint(sample.samples_bp)
    app.register_blueprint(alignviewers.alignviewers_bp)
    app.register_blueprint(groups.groups_bp)
    app.register_blueprint(cluster.cluster_bp)
    app.register_blueprint(api.api_bp)
    app.register_blueprint(admin.admin_bp)


def register_filters(app):
    """Register jinja2 filter functions."""
    for name, func in JINJA_FILTERS.items():
        app.jinja_env.filters[name] = func


def register_tests(app):
    """Register custom test functions."""
    for name, func in JINJA_TESTS.items():
        app.jinja_env.tests[name] = func

    return app
