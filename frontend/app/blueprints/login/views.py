from app import __version__ as VERSION
from app.bonsai import TokenObject, get_auth_token, get_current_user
from app.extensions import login_manager
from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from flask_login import UserMixin, login_required, login_user, logout_user
from requests.exceptions import HTTPError

login_bp = Blueprint(
    "login",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/login",
)


class LoginUser(UserMixin):
    def __init__(self, user_data, token_data):
        """Create a new user object."""
        self.roles = []
        for key, value in user_data.items():
            setattr(self, key, value)
        # store token
        self.token = token_data

    def get_id(self):
        return self.token.dict()

    @property
    def is_admin(self):
        """Check if the user is admin."""
        return "admin" in self.roles


@login_bp.route("/login")
def login_page():
    """Landing page view."""
    return render_template("login.html", title="Login", version=VERSION)


@login_bp.route("/logout")
@login_required
def logout():
    """Logout user."""
    logout_user()
    session.pop("email", None)
    session.pop("fname", None)
    session.pop("lname", None)
    session.pop("locale", None)
    return redirect(url_for("public.index"))


@login_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login a user."""
    if "next" in request.args:
        session["next_url"] = request.args["next"]

    # get login credentials from form
    username = request.form["username"]
    password = request.form["password"]

    try:
        token_obj: TokenObject = get_auth_token(username, password)
    except HTTPError as err:
        # if invalid credentials
        if err.response.status_code == 401:
            flash("Invalid login credentials", "danger")
        else:
            # TODO redirect to report bug page
            # TODO log errors...
            flash("Sorry, you could not log in due to an internal error", "warning")

        return redirect(url_for("public.index"))

    user_obj = get_current_user(token_obj)
    user = LoginUser(user_obj, token_obj)
    return perform_login(user)


@login_manager.user_loader
def load_user(user_id):
    """Reload user object from user id stored in session."""
    token = TokenObject(**user_id)
    try:
        user_obj = get_current_user(token)
    except HTTPError as error:
        return None

    user = LoginUser(user_obj, token) if user_obj else None
    return user


def perform_login(user):
    if login_user(user):
        next_url = session.pop("next_url", None)
        return redirect(
            request.args.get("next") or next_url or url_for("groups.groups")
        )

    # could not log in
    flash("sorry, you could not log in", "warning")
    return redirect(url_for("public.index"))


@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect(url_for("login.login_page"))
