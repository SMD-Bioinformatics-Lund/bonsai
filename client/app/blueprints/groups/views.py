"""Declaration of views for groups"""
from flask import Blueprint, current_app, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.mimer import get_groups, TokenObject

groups_bp = Blueprint("groups", __name__, template_folder="templates", static_folder="static")

@groups_bp.route('/groups')
@login_required
def groups():
    """Groups view."""
    # if not valid token
    if current_user.get_id() is None:
        return redirect(url_for("public.index"))

    token = TokenObject(**current_user.get_id())
    groups = get_groups(token)
    return render_template("groups.html", groups=groups)


@groups_bp.route('/groups/<group_id>')
@login_required
def group(group_id):
    """Group view."""
    return render_template("group.html", group_id=group_id)