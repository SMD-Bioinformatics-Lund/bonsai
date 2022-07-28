from flask import Blueprint, session, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, UserMixin
from app.extensions import login_manager
from app.mimer import get_auth_token, get_current_user

login_bp = Blueprint("login", __name__, template_folder="templates", static_folder="static")


class LoginUser(UserMixin):
    def __init__(self, user_data):
        """Create a new user object."""
        self.roles = []
        for key, value in user_data.items():
            setattr(self, key, value)

    def get_id(self):
        return self.email

    @property
    def is_admin(self):
        """Check if the user is admin."""
        return "admin" in self.roles 


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


@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login a user."""
    if "next" in request.args:
        session["next_url"] = request.args["next"]
    
    username = None
    password = None

    token = get_auth_token(username, password)
    user_obj = get_current_user(token)
    user = LoginUser(user_obj)
    return perform_login(user)


@login_manager.user_loader
def load_user(user_id):
    """Reload user object from user id stored in session."""
    user_obj = get_current_user(user_id)
    user = LoginUser(user_obj) if user_obj else None
    return user

def perform_login(user_dict):
    if login_user(user_dict):
        flash(f"you logged in as: {user_dict.name}", "success")
        next_url = session.pop("next_url", None)
        return redirect(request.args.get("next") or next_url or url_for("cases.index"))

    # could not log in
    flash("sorry, you could not log in", "warning")
    return redirect(url_for("public.index"))