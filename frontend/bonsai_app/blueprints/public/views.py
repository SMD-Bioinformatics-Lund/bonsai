"""Public accessable assets and views."""

from flask import Blueprint, render_template, request, send_from_directory

from ... import __version__ as VERSION

public_bp = Blueprint(
    "public",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/",
)


@public_bp.route("/")
def index():
    """Landing page view."""
    return render_template("index.html", version=VERSION)


@public_bp.route("/favicon", methods=["GET"])
def favicon():
    """Route for accessing favicon."""
    return send_from_directory(public_bp.static_folder, request.args.get("filename"))


@public_bp.route("/webmanifest")
def webmanifest():
    """Route for accessing webmanifest."""
    return send_from_directory(public_bp.static_folder, "site.webmanifest")
