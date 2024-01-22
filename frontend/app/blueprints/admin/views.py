"""Declaration of flask admin views"""
from flask import Blueprint, flash, redirect, url_for, render_template, request
from flask_login import current_user, login_required
from app.bonsai import get_user, get_users, TokenObject
from wtforms import Form, BooleanField, StringField, PasswordField, validators, widgets, SelectMultipleField


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

class UserRegistrationForm(Form):
    """Register a new user."""
    username = StringField('Username', [validators.Length(min=4, max=25)])
    first_name = StringField('First name', [validators.Length(min=4, max=50)])
    last_name = StringField('Last name', [validators.Length(min=4, max=50)])
    email = StringField('Email Address', [validators.Length(min=6, max=35)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
    roles = MultiCheckboxField('Roles', choices=['admin', 'user', 'uploader'])


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
        flash("Created new user", "success")
    # get all users
    return render_template("create_user.html", method='create', form=form)


@admin_bp.route("/admin/users/<username>", methods=["GET", "POST"])
@login_required
def edit_user(username):
    """Edit existing user."""
    # if not valid token
    if not current_user.is_admin:
        flash("You dont have permission to view this page", "warning")
        return redirect(url_for('public.home'))

    token = TokenObject(**current_user.get_id())
    # get all users
    user = get_user(token, username=username)
    form = UserRegistrationForm(request.form)
    # populate form with deafults from the database
    form.username.data = user['username']
    form.first_name.data = user['first_name']
    form.last_name.data = user['last_name']
    form.email.data = user['email']
    form.roles.data = user['roles']

    if request.method == "POST" and form.validate():
        flash("Updated existing user", "success")
    # get all users
    return render_template("create_user.html", method='edit', form=form)