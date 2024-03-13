"""Declaration of flask admin views"""
from app.bonsai import TokenObject
from app.bonsai import create_user as create_new_user
from app.bonsai import delete_user as delete_user_from_db
from app.bonsai import get_user, get_users
from app.bonsai import update_user as update_user_info
from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required
from requests.exceptions import HTTPError
from wtforms import (Form, PasswordField, SelectMultipleField, StringField,
                     ValidationError, validators, widgets)

admin_bp = Blueprint(
    "admin",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/admin/static",
)


@admin_bp.route("/admin")
@login_required
def admin_panel():
    """Default admin panel view."""
    # if not valid token
    if not current_user.is_admin:
        flash("You dont have permission to view this page", "warning")
        return redirect(url_for("public.home"))

    return redirect(url_for("admin.view_users"))


@admin_bp.route("/admin/users")
@login_required
def view_users():
    """Edit Bonsai users."""
    # if not valid token
    if not current_user.is_admin:
        flash("You dont have permission to view this page", "warning")
        return redirect(url_for("public.home"))

    token = TokenObject(**current_user.get_id())
    # get all users
    users = get_users(token)
    return render_template("users_list.html", users=users)


PASSWORD_VALIDATORS = [
    validators.Length(min=8, max=72),
    validators.Regexp(
        r"^((?=\S*?[A-Z])(?=\S*?[a-z])(?=\S*?[0-9]).+)\S$",
        message="The password must include upper- and lower case letters with at leats one number.",
    ),
    validators.EqualTo("confirm", message="Passwords must match"),
]


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class UserInfoForm(Form):
    """Register a new user."""

    username = StringField("Username", [validators.Length(min=4, max=25)])
    first_name = StringField("First name", [validators.Length(min=2, max=50)])
    last_name = StringField("Last name", [validators.Length(min=2, max=50)])
    email = StringField("Email Address", [validators.Email()])
    password = PasswordField("Password", [validators.Optional(), *PASSWORD_VALIDATORS])

    confirm = PasswordField("Repeat Password")
    roles = MultiCheckboxField("Roles", choices=["admin", "user", "uploader"])

    def validate_roles(form, field):
        """Validate that one or more roles is selected."""
        if field.data is None or len(field.data) == 0:
            raise ValidationError("At least one role must be selected")


class UserRegistrationForm(UserInfoForm):
    password = PasswordField("Password", PASSWORD_VALIDATORS)

    def validate_username(form, field):
        """Check if username already exists."""
        username = field.data
        token = TokenObject(**current_user.get_id())
        user_exists = True
        try:
            get_user(token, username=username)
        except HTTPError as error:
            if error.response.status_code == 404:
                user_exists = False
            else:
                raise error
        if user_exists:
            raise ValidationError(f"An user with username {username} already exists")


@admin_bp.route("/admin/users/new", methods=["GET", "POST"])
@login_required
def create_user():
    """Create new users."""
    # if not valid token
    if not current_user.is_admin:
        flash("You dont have permission to view this page", "warning")
        return redirect(url_for("public.home"))

    form = UserRegistrationForm(request.form)
    if request.method == "POST" and form.validate():
        token = TokenObject(**current_user.get_id())
        try:
            status = create_new_user(token, user_obj=form.data)
        except HTTPError as error:
            flash(
                f"Error when creating a new user, {error.response.status_code}",
                "warning",
            )
        else:
            flash("Created new user", "success")
        return redirect(url_for("admin.view_users"))
    # get all users
    return render_template("user_form.html", method="create", form=form)


@admin_bp.route("/admin/users/delete", methods=["POST"])
@login_required
def delete_users():
    """Delete users."""
    # if not valid token
    if not current_user.is_admin:
        flash("You dont have permission to view this page", "warning")
        return redirect(url_for("public.home"))

    token = TokenObject(**current_user.get_id())
    removed_users = []
    for username, value in request.form.items():
        if value == "on":
            try:
                delete_user_from_db(token, username=username)
            except Exception as error:
                flash(f"Error when deleting user: {username}", "danger")
                raise ValueError(error)
            else:
                removed_users.append(username)

    # inform user which samples was removed
    if len(removed_users) > 0:
        names = ", ".join(removed_users)
        flash(f"Deleted users: {names}", "success")
    # get all users
    return redirect(request.referrer)


@admin_bp.route("/admin/users/<username>", methods=["GET", "POST"])
@login_required
def update_user(username):
    """Edit existing user."""
    # if not valid token
    if not current_user.is_admin:
        flash("You dont have permission to view this page", "warning")
        return redirect(url_for("public.home"))

    token = TokenObject(**current_user.get_id())
    # get all users
    user = get_user(token, username=username)
    form = UserInfoForm(request.form)

    if request.method == "POST":
        if not form.validate():
            flash("Invalid input data", "warning")
        elif "update" in request.form:
            try:
                update_user_info(token, username=username, user=form.data)
            except Exception as error:
                flash("An error occurred when updating user info", "warning")
                current_app.logger.error("Error updating user: %s", str(error))
            else:
                flash(f"Updated user {username}", "success")
                current_app.logger.debug("Updated user: %s", username)
        else:
            try:
                delete_user_from_db(token, username=username)
            except:
                flash(f"An error occurred when removing {username}", "warning")
            else:
                flash(f"Removed user {username}", "success")
    elif request.method == "GET":
        # populate form with deafults from the database
        form.username.data = user["username"]
        form.first_name.data = user["first_name"]
        form.last_name.data = user["last_name"]
        form.email.data = user["email"]
        form.roles.data = user["roles"]
    # get all users
    return render_template("user_form.html", method="edit", form=form)
