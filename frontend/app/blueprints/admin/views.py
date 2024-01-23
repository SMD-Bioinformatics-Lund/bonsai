"""Declaration of flask admin views"""
from flask import Blueprint, flash, redirect, url_for, render_template, request, current_app
from flask_login import current_user, login_required
from app.bonsai import get_user, get_users, TokenObject
from app.bonsai import delete_user as delete_user_from_db
from app.bonsai import update_user as update_user_info
from app.bonsai import create_user as create_new_user
from wtforms import Form, StringField, PasswordField, validators, widgets, SelectMultipleField


admin_bp = Blueprint("admin", __name__, template_folder="templates", static_folder="static", static_url_path="/admin/static")


@admin_bp.route("/admin")
@login_required
def admin_panel():
    """Default admin panel view."""
    # if not valid token
    if not current_user.is_admin:
        flash("You dont have permission to view this page", "warning")
        return redirect(url_for('public.home'))

    return render_template("admin_panel.html")


@admin_bp.route("/admin/users")
@login_required
def view_users():
    """Edit Bonsai users."""
    # if not valid token
    if not current_user.is_admin:
        flash("You dont have permission to view this page", "warning")
        return redirect(url_for('public.home'))

    token = TokenObject(**current_user.get_id())
    # get all users
    users = get_users(token)
    return render_template("users_list.html", users=users)

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class UserInfoForm(Form):
    """Register a new user."""
    username = StringField('Username', [validators.Length(min=4, max=25)])
    first_name = StringField('First name', [validators.Length(min=4, max=50)])
    last_name = StringField('Last name', [validators.Length(min=4, max=50)])
    email = StringField('Email Address', [validators.Length(min=6, max=35)])
    password = PasswordField('Password', [
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
    roles = MultiCheckboxField('Roles', choices=['admin', 'user', 'uploader'])


class UserRegistrationForm(UserInfoForm):

    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])


@admin_bp.route("/admin/users/new", methods=["GET", "POST"])
@login_required
def create_user():
    """Create new users."""
    # if not valid token
    if not current_user.is_admin:
        flash("You dont have permission to view this page", "warning")
        return redirect(url_for('public.home'))

    form = UserRegistrationForm(request.form)
    if request.method == "POST" and form.validate():
        token = TokenObject(**current_user.get_id())
        status = create_new_user(token, user_obj=form.data)
        flash("Created new user", "success")
        return redirect(url_for("admin.view_users"))
    # get all users
    return render_template("user_form.html", method='create', form=form)


@admin_bp.route("/admin/users/delete", methods=["POST"])
@login_required
def delete_users():
    """Delete users."""
    # if not valid token
    if not current_user.is_admin:
        flash("You dont have permission to view this page", "warning")
        return redirect(url_for('public.home'))

    token = TokenObject(**current_user.get_id())
    removed_users = []
    for username, value in request.form.items():
        if value == "on":
            try:
                delete_user_from_db(token, username=username)
            except Exception as error:
                flash(f"Error when deleting user: {username}", "danger")
                raise  ValueError(error)
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
        return redirect(url_for('public.home'))

    token = TokenObject(**current_user.get_id())
    # get all users
    user = get_user(token, username=username)
    form = UserInfoForm(request.form)

    if request.method == "POST" and form.validate():
        if "update" in request.form:
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
    else:
        # populate form with deafults from the database
        form.username.data = user['username']
        form.first_name.data = user['first_name']
        form.last_name.data = user['last_name']
        form.email.data = user['email']
        form.roles.data = user['roles']
    # get all users
    return render_template("user_form.html", method='edit', form=form)