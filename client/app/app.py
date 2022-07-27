"""Code for setting up the flask app."""
from flask import Flask, current_app
from .blueprints import public

def create_app():
    """Flask app factory function."""

    app = Flask(__name__)
    # load default config
    app.config.from_pyfile("config.py")

    register_blueprints(app)

    return app


def register_blueprints(app):
    """Register flask blueprints."""
    app.register_blueprint(public.public_bp)