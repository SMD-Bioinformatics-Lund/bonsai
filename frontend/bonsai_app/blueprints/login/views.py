"""Manage user authentication."""

import logging

from bonsai_libs.api_client.core import BearerTokenAuth
from bonsai_libs.api_client.core.exceptions import UnauthorizedError
from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import UserMixin, login_required, login_user, logout_user

from bonsai_app import __version__ as VERSION
from bonsai_app.bonsai_api import BonsaiApiClient
from bonsai_app.extensions import login_manager

LOG = logging.getLogger(__name__)

login_bp = Blueprint(
    "login",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/login",
)


class LoginUser(UserMixin):
    """Container for user data and perform login."""

    def __init__(self, user_data: dict[str, str], token: str):
        """Create a new authenticated user.

        :param user_data: User data returned from API
        :param token: Access token for API authentication
        """

        self.username = user_data["username"]
        self.id = self.username
        self.token = token

        self.roles = user_data.get("roles", [])

        for key, value in user_data.items():
            setattr(self, key, value)

    def get_id(self):
        """Get user id."""
        return self.username

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
    session.clear()
    return redirect(url_for("public.index"))


@login_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login a user."""
    if "next" in request.args:
        session["next_url"] = request.args["next"]

    if request.method == "GET":
        return render_template("login.html", ...)

    # get login credentials from form
    username = request.form["username"]
    password = request.form["password"]

    client = BonsaiApiClient(
        base_url=current_app.config["API_INTERNAL_URL"],
    )
    client.authenticate_user(username, password)
    try:
        client.authenticate_user(username, password)
        user_obj = client.get_current_user()
        user = LoginUser(user_obj.model_dump(mode="json"), token=client.auth.token)
    except UnauthorizedError:
        # if invalid credentials
        flash("Invalid login credentials", "danger")
        return redirect(url_for("public.index"))
    except Exception as err:
        LOG.warning("An unexpected error during login: %s", err)
        flash("Sorry, you could not log in due to an internal error", "warning")
        return redirect(url_for("public.index"))

    # set token in session
    session["access_token"] = client.auth.token

    return perform_login(user)


@login_manager.user_loader
def load_user(user_id: str) -> LoginUser:
    """Reconstruct user from session.

    :param user_id: Identifier stored in session
    :return: LoginUser or None
    """
    token = session.get("access_token")

    client = BonsaiApiClient(
        base_url=current_app.config["API_INTERNAL_URL"],
        auth=BearerTokenAuth(token),
    )
    try:
        user_data = client.get_current_user()
    except UnauthorizedError:
        # Clear bad token from session
        session.clear()
        return redirect(url_for("public.index"))

    return LoginUser(user_data.model_dump(mode="json"), token)


def perform_login(user: LoginUser) -> Response:
    """Login user.

    :param user: User
    :type user: LoginUser
    :return: redirect user to /groups if login is successfull
    :rtype: Response
    """
    if login_user(user):
        next_url = session.pop("next_url", None)
        return redirect(
            request.args.get("next") or next_url or url_for("groups.groups")
        )

    # could not log in
    flash("sorry, you could not log in", "warning")
    LOG.warning("User authentication failed.")
    return redirect(url_for("public.index"))


@login_manager.unauthorized_handler
def unauthorized_handler() -> Response:
    """Define function for handeling unauthorized users.

    :return: redirect failed auth attempt to login page
    :rtype: Response
    """
    return redirect(url_for("login.login_page"))
