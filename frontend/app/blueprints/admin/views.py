"""Declaration of flask admin views"""
from flask import Blueprint, flash, redirect, url_for, render_template
from flask_login import current_user, login_required


admin_bp = Blueprint("admin", __name__, template_folder="templates", static_folder="static")


@admin_bp.route("/admin")
@login_required
def admin_panel():
    """Add sample to basket."""
    # if not valid token
    if not current_user.is_admin:
        flash("You dont have permission to view this page", "warning")
        return redirect(url_for('public.home'))

    return render_template("admin_panel.html")