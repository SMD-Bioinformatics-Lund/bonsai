"""Declaration of views for groups"""
from flask import Blueprint, current_app, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.mimer import get_samples_by_id, get_groups, get_samples_in_group, delete_group, update_group, TokenObject
import json

groups_bp = Blueprint(
    "groups", __name__, template_folder="templates", static_folder="static", static_url_path="/groups/static"
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
    samples = get_samples_by_id(token, limit=100)
    return render_template("groups.html", title="Groups", groups=groups, samples=samples)

@groups_bp.route("/groups/edit", methods=['GET', 'POST'])
@groups_bp.route("/groups/edit/<group_id>", methods=['GET', 'POST'])
@login_required
def edit_groups(group_id=None):
    """Groups view."""
    # if not valid token or if user is not admin
    if current_user.get_id() is None or not current_user.is_admin:
        return redirect(url_for("public.index"))

    token = TokenObject(**current_user.get_id())
    groups = get_groups(token)

    # remove group from database
    if request.method == 'POST':
        # if a group should be removed
        if 'input-remove-group' in request.form:
            try:
                delete_group(token, group_id=request.form.get('input-remove-group'))
                flash('Group updated', 'success')
            except Exception as err:
                flash(f'An error occured when updating group, {err}', 'danger')
            return redirect(url_for('groups.edit_groups'))
        elif 'input-update-group' in request.form:
            updated_data = json.loads(request.form.get('input-update-group'))
            try:
                update_group(token, group_id=group_id, data=updated_data)
                flash(f'Group updated', 'success')
                return redirect(url_for('groups.edit_groups'))
            except Exception as err:
                flash(f'An error occured when updating group, {err}', 'danger')
    return render_template("edit_groups.html", title="Groups", selected_group=group_id, groups=groups)


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
    #raise Exception
    return render_template(
        "group.html",
        title=group_id,
        group_id=group_id,
        samples=group["includedSamples"],
        table_definition=table_definition,
    )
