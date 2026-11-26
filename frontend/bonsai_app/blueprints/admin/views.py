"""Declaration of flask admin views"""

from bonsai_libs.api_client.bonsai.models import CreateUserInput
from bonsai_libs.api_client.core.exceptions import ApiError, NotFoundError
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from wtforms import (
    Form,
    PasswordField,
    SelectMultipleField,
    StringField,
    ValidationError,
    validators,
    widgets,
)

from bonsai_app.bonsai_api import get_api_client

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
        flash("You don't have permission to view this page", "warning")
        return redirect(url_for("public.index"))

    return redirect(url_for("admin.view_users"))


@admin_bp.route("/admin/users")
@login_required
def view_users():
    """Edit Bonsai users."""
    # if not valid token
    if not current_user.is_admin:
        flash("You don't have permission to view this page", "warning")
        return redirect(url_for("public.index"))

    client = get_api_client()
    users = client.get_users()

    return render_template("users_list.html", users=users)


PASSWORD_VALIDATORS = [
    validators.Length(min=8, max=72),
    validators.Regexp(
        r"^((?=\S*?[A-Z])(?=\S*?[a-z])(?=\S*?[0-9]).+)\S$",
        message="The password must include uppercase and lowercase letters and at least one number.",
    ),
    validators.EqualTo("confirm", message="Passwords must match"),
]


class MultiCheckboxField(SelectMultipleField):  # pylint: disable=too-few-public-methods
    """WTforms MultiCheckboxField."""

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


class UserRegistrationForm(UserInfoForm):  # pylint: disable=too-few-public-methods
    """Form for registering a new user."""

    password = PasswordField("Password", PASSWORD_VALIDATORS)

    def validate_username(form, field):
        """Check if username already exists."""
        if field.errors:
            return
        username = field.data
        user_exists = True
        try:
            client = get_api_client()
            client.get_user(username)
        except NotFoundError:
            user_exists = False
        except ApiError as error:
            raise ValidationError(
                "Could not check username availability. Please try again."
            ) from error
        if user_exists:
            raise ValidationError(f"A user with username {username} already exists")


@admin_bp.route("/admin/users/new", methods=["GET", "POST"])
@login_required
def create_user():
    """Create new users."""
    # if not valid token
    if not current_user.is_admin:
        flash("You don't have permission to view this page", "warning")
        return redirect(url_for("public.index"))

    form = UserRegistrationForm(request.form)
    if request.method == "POST" and form.validate():
        try:
            user_data = CreateUserInput.model_validate(form.data)

            client = get_api_client()
            client.create_user(user_data)
        except ApiError:
            flash(
                "An error occurred when creating the user. Please try again.",
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
        flash("You don't have permission to view this page", "warning")
        return redirect(url_for("public.index"))

    client = get_api_client()

    removed_users = []
    for username, value in request.form.items():
        if value == "on":
            try:
                client.delete_user(username)
            except ApiError:
                flash(f"Error when deleting user: {username}", "danger")
                continue
            removed_users.append(username)

    # inform user which samples was removed
    if len(removed_users) > 0:
        names = ", ".join(removed_users)
        flash(f"Deleted users: {names}", "success")
    # get all users
    return redirect(url_for("admin.view_users"))


@admin_bp.route("/admin/users/<username>", methods=["GET", "POST"])
@login_required
def update_user(username):
    """Edit existing user."""
    # if not valid token
    if not current_user.is_admin:
        flash("You don't have permission to view this page", "warning")
        return redirect(url_for("public.index"))

    client = get_api_client()

    # get all users
    user = client.get_user(username)
    form = UserInfoForm(request.form)

    if request.method == "POST":
        if not form.validate():
            flash("Invalid input data", "warning")
        elif "update" in request.form:
            try:
                client.update_user(username=username, user_data=form.data)
            except Exception as error:
                flash("An error occurred when updating user info", "warning")
                current_app.logger.error("Error updating user: %s", str(error))
            else:
                flash(f"Updated user {username}", "success")
                current_app.logger.debug("Updated user: %s", username)
        elif "delete" in request.form:
            try:
                client.delete_user(username)
            except:
                flash(f"An error occurred when removing {username}", "warning")
            else:
                flash(f"Removed user {username}", "success")
    elif request.method == "GET":
        # populate form with defaults from the database
        form.username.data = user.username
        form.first_name.data = user.first_name
        form.last_name.data = user.last_name
        form.email.data = user.email
        form.roles.data = user.roles
        if current_user.authentication_method == "ldap":
            form.password.render_kw = {"disabled": True}
            form.confirm.render_kw = {"disabled": True}
            flash(
                f"Passwords are managed by the {current_user.authentication_method} server",
                "info",
            )

    # get all users
    return render_template("user_form.html", method="edit", form=form)
