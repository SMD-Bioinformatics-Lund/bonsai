"""Public accessable assets and views."""

from flask import Blueprint, render_template, request, send_from_directory, current_app

from bonsai_app import __version__ as VERSION

public_bp = Blueprint(
    "public",
    __name__,
    template_folder="templates",
)


@public_bp.route("/")
def index():
    """Landing page view."""
    return render_template("index.html", version=VERSION)


@public_bp.route("/favicon", methods=["GET"])
def favicon():
    """Route for accessing favicon."""
    return send_from_directory(current_app.static_folder, request.args.get("filename"))


@public_bp.route("/webmanifest")
def webmanifest():
    """Route for accessing webmanifest."""
    return send_from_directory(current_app.static_folder, "site.webmanifest")
