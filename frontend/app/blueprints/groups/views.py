"""Declaration of views for groups"""
import json

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

from app.bonsai import (
    TokenObject,
    create_group,
    delete_group,
    get_groups,
    get_samples,
    get_samples_by_id,
    get_samples_in_group,
    update_group,
)
from app.models import PhenotypeType

groups_bp = Blueprint(
    "groups",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/groups/static",
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
    samples = get_samples(token, limit=0, skip=0)
    basket = session

    return render_template(
        "groups.html",
        title="Groups",
        groups=groups,
        samples=samples,
        basket=basket,
        token=current_user.get_id().get("token"),
    )


@groups_bp.route("/groups/edit", methods=["GET", "POST"])
@groups_bp.route("/groups/edit/<group_id>", methods=["GET", "POST"])
@login_required
def edit_groups(group_id=None):
    """Groups view."""
    # if not valid token or if user is not admin
    if current_user.get_id() is None or not current_user.is_admin:
        return redirect(url_for("public.index"))

    token = TokenObject(**current_user.get_id())
    groups = get_groups(token)

    # remove group from database
    if request.method == "POST":
        # if a group should be removed
        if "input-remove-group" in request.form:
            try:
                delete_group(token, group_id=request.form.get("input-remove-group"))
                flash("Group updated", "success")
            except Exception as err:
                flash(f"An error occured when updating group, {err}", "danger")
            return redirect(url_for("groups.edit_groups"))
        elif "input-update-group" in request.form:
            updated_data = json.loads(request.form.get("input-update-group"))
            try:
                update_group(token, group_id=group_id, data=updated_data)
                flash(f"Group updated", "success")
                return redirect(url_for("groups.edit_groups"))
            except Exception as err:
                flash(f"An error occured when updating group, {err}", "danger")
        elif "input-create-group" in request.form:
            input_data = json.loads(request.form.get("input-create-group", {}))
            try:
                create_group(token, data=input_data)
                flash(f"Group updated", "success")
                return redirect(url_for("groups.edit_groups"))
            except Exception as err:
                flash(f"An error occured when updating group, {err}", "danger")
    # get valid phenotypes
    valid_phenotypes = {
        entry.name.lower().capitalize().replace("_", " "): entry.value
        for entry in PhenotypeType.__members__.values()
    }
    return render_template(
        "edit_groups.html",
        title="Groups",
        selected_group=group_id,
        groups=groups,
        valid_phenotypes=valid_phenotypes,
    )


@groups_bp.route("/groups/<group_id>")
@login_required
def group(group_id):
    """Group view."""
    token = TokenObject(**current_user.get_id())
    group = get_samples_in_group(token, group_id=group_id, lookup_samples=False)
    table_definition = group["table_columns"]
    samples = get_samples_by_id(
        token, limit=0, skip=0, sample_ids=group["included_samples"]
    )
    # TODO add flag to exclude cgmlst from api call
    # TODO implement table definition to dynamically generate a table
    # TODO add pagination
    return render_template(
        "group.html",
        title=group_id,
        group_name=group["display_name"],
        samples=samples["records"],
        modified=group["modified_at"],
        table_definition=table_definition,
    )
