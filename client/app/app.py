"""Code for setting up the flask app."""
from flask import Flask, current_app
from .blueprints import public, login, groups, sample, cluster
from .extensions import login_manager
from dateutil.parser import parse


def create_app():
    """Flask app factory function."""

    app = Flask(__name__)
    # load default config
    app.config.from_pyfile("config.py")
    # setup secret key
    app.secret_key = app.config["SECRET_KEY"]

    # initialize flask extensions
    login_manager.init_app(app)

    # configure pages etc
    register_blueprints(app)

    @app.template_filter("strftime")
    def _jinja2_filter_datetime(date, fmt=None):
        date = parse(date)
        native = date.replace(tzinfo=None)
        format = "%b %d, %Y"
        return native.strftime(format)

    return app


def register_blueprints(app):
    """Register flask blueprints."""
    app.register_blueprint(public.public_bp)
    app.register_blueprint(login.login_bp)
    app.register_blueprint(sample.samples_bp)
    app.register_blueprint(groups.groups_bp)
    app.register_blueprint(cluster.cluster_bp)