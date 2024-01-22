"""Declaration of flask admin views"""
from flask import Blueprint, flash, redirect, url_for, render_template
from flask_login import current_user, login_required
from app.bonsai import get_users, TokenObject


admin_bp = Blueprint("admin", __name__, template_folder="templates", static_folder="static")


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
def edit_users():
    """Edit Bonsai users."""
    # if not valid token
    if not current_user.is_admin:
        flash("You dont have permission to view this page", "warning")
        return redirect(url_for('public.home'))

    token = TokenObject(**current_user.get_id())
    # get all users
    users = get_users(token)

    return render_template("edit_users.html", users=users)