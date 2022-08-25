"""Declaration of views for groups"""
from flask import Blueprint, current_app, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.mimer import get_groups, get_samples_in_group, TokenObject

groups_bp = Blueprint(
    "groups", __name__, template_folder="templates", static_folder="static"
)


@groups_bp.route("/groups")
@login_required
def groups():
    """Groups view."""
    # if not valid token
    if current_user.get_id() is None:
        return redirect(url_for("public.index"))

    token = TokenObject(**current_user.get_id())
    groups = get_groups(token)
    return render_template("groups.html", groups=groups)


@groups_bp.route("/groups/<group_id>")
@login_required
def group(group_id):
    """Group view."""
    token = TokenObject(**current_user.get_id())
    group = get_samples_in_group(token, group_id=group_id, lookup_samples=True)
    # TODO add flag to exclude cgmlst from api call
    # TODO implement table definition to dynamically generate a table
    # TODO add pagination
    table_definition = group["tableColumns"]
    return render_template(
        "group.html",
        group_id=group_id,
        samples=group["includedSamples"],
        table_definition=table_definition,
    )
