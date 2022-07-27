"""Code for setting up the flask app."""
from flask import Flask, current_app

def create_app():
    """Flask app factory function."""

    app = Flask(__name__)

    @app.route("/")
    def home():
        return "<p>Hello World</p>"

    return app