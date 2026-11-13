"""Public accessable assets and views."""

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from bonsai_app import __version__ as VERSION

public_bp = Blueprint(
    "public",
    __name__,
    template_folder="templates",
)


@public_bp.route("/")
def index():
    """Redirect the application root to the primary Groups view."""
    return redirect(url_for("groups.groups"))


@public_bp.route("/about")
def about():
    """Display information and resources about Bonsai."""
    return render_template("index.html", title="About", version=VERSION)


@public_bp.route("/favicon", methods=["GET"])
def favicon():
    """Route for accessing favicon."""
    return send_from_directory(current_app.static_folder, request.args.get("filename"))


@public_bp.route("/webmanifest")
def webmanifest():
    """Route for accessing webmanifest."""
    return send_from_directory(current_app.static_folder, "site.webmanifest")
