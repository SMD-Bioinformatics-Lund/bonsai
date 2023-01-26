from flask import Blueprint, current_app, render_template, send_from_directory, request
from app import VERSION

public_bp = Blueprint(
    "public", __name__, template_folder="templates", static_folder="static"
)


@public_bp.route("/")
def index():
    """Landing page view."""
    return render_template("index.html", version=VERSION)


@public_bp.route("/login")
def login():
    """Landing page view."""
    return render_template("login.html", version=VERSION)


@public_bp.route("/favicon", methods=["GET"])
def favicon():
    return send_from_directory(public_bp.static_folder, request.args.get("filename"))

@public_bp.route("/webmanifest")
def webmanifest():
    return send_from_directory(public_bp.static_folder, "site.webmanifest")
