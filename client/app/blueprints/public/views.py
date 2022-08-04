from flask import Blueprint, current_app, render_template, send_from_directory, request
from app import VERSION

public_bp = Blueprint(
    "public", __name__, template_folder="templates", static_folder="static"
)


@public_bp.route("/")
def index():
    """Landing page view."""
    return render_template("index.html", version=VERSION)


@public_bp.route("/favicon")
def favicon():
    return send_from_directory(current_app.static_folder, "favicon.ico")
