"""Declaration of views for groups"""
import json
import logging
from urllib.parse import urlparse

from app.bonsai import (
    TokenObject,
    create_group,
    delete_group,
    get_groups,
    get_samples,
    get_samples_by_id,
    get_samples_in_group,
    get_valid_group_columns,
    update_group,
    update_sample_qc_classification,
)
from app.models import BadSampleQualityAction, PhenotypeType, QualityControlResult
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required
from requests.exceptions import HTTPError

LOG = logging.getLogger(__name__)

groups_bp = Blueprint(
    "groups",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/groups/static",
)


@groups_bp.route("/groups")
@login_required
def groups() -> str:
    """Generate page that displays groups and all samples.

    :return: generated HTML page
    :rtype: str
    """
    # if not valid token
    if current_user.get_id() is None:
        LOG.info(
            "User not logged in: %s %s", current_user.first_name, current_user.last_name
        )
        return redirect(url_for("public.index"))

    token = TokenObject(**current_user.get_id())
    all_groups = get_groups(token)
    all_samples = get_samples(token, limit=0, skip=0)
    basket = session

    bad_qc_actions = [member.value for member in BadSampleQualityAction]

    # Pre-select samples in sample table:
    selected_samples = request.args.getlist("samples")

    return render_template(
        "groups.html",
        title="Groups",
        groups=all_groups,
        samples=all_samples,
        basket=basket,
        token=current_user.get_id().get("token"),
        bad_qc_actions=bad_qc_actions,
        selected_samples=selected_samples,
    )


@groups_bp.route("/groups/edit", methods=["GET", "POST"])
@groups_bp.route("/groups/edit/<group_id>", methods=["GET", "POST"])
@login_required
def edit_groups(group_id: str | None = None) -> str:
    """Generate edit groups view

    :param group_id: Group id, defaults to None
    :type group_id: str, optional
    :return: generated HTML page
    :rtype: str
    """
    # if not valid token or if user is not admin
    if current_user.get_id() is None or not current_user.is_admin:
        return redirect(url_for("public.index"))

    token = TokenObject(**current_user.get_id())
    all_groups = get_groups(token)

    # remove group from database
    if request.method == "POST":
        # if a group should be removed
        if "input-remove-group" in request.form:
            try:
                delete_group(token, group_id=request.form.get("input-remove-group"))
                flash("Group updated", "success")
            except HTTPError as err:
                flash(f"An error occured when updating group, {err}", "danger")
            return redirect(url_for("groups.edit_groups"))
        elif "input-update-group" in request.form:
            updated_data = json.loads(request.form.get("input-update-group"))
            try:
                update_group(token, group_id=group_id, data=updated_data)
                flash("Group updated", "success")
                return redirect(url_for("groups.edit_groups", group_id=group_id))
            except HTTPError as err:
                flash(f"An error occured when updating group, {err}", "danger")
        elif "input-create-group" in request.form:
            input_data = json.loads(request.form.get("input-create-group", {}))
            try:
                group_id = input_data["group_id"]
                create_group(token, data=input_data)
                flash("Group updated", "success")
                return redirect(url_for("groups.edit_groups", group_id=group_id))
            except HTTPError as err:
                flash(f"An error occured when updating group, {err}", "danger")

    # get valid phenotypes
    valid_phenotypes = {
        entry.name.lower().capitalize().replace("_", " "): entry.value
        for entry in PhenotypeType.__members__.values()
    }

    # get valid columns and set used cols as checked
    valid_cols = get_valid_group_columns()
    all_group_ids = [group["group_id"] for group in all_groups]
    if group_id is not None and group_id in all_group_ids:
        selected_group = next(
            iter(group for group in all_groups if group["group_id"] == group_id)
        )
        cols_in_group = [gr["path"] for gr in selected_group["table_columns"]]
    else:
        cols_in_group = []
    # annotate if column previously have been selected
    for column in valid_cols:
        column["selected"] = column["path"] in cols_in_group
    return render_template(
        "edit_groups.html",
        title="Groups",
        selected_group=group_id,
        groups=all_groups,
        valid_columns=valid_cols,
        valid_phenotypes=valid_phenotypes,
    )


@groups_bp.route("/groups/<group_id>")
@login_required
def group(group_id: str) -> str:
    """Group view.

    :param group_id: Group id
    :type group_id: str
    :return: html page
    :rtype: str
    """
    token = TokenObject(**current_user.get_id())
    try:
        group_info = get_samples_in_group(
            token, group_id=group_id, lookup_samples=False
        )
    except HTTPError as error:
        # throw proper error page
        abort(error.response.status_code)
    table_definition = group_info["table_columns"]
    samples = get_samples_by_id(
        token, limit=0, skip=0, sample_ids=group_info["included_samples"]
    )

    # Pre-select samples in sample table:
    selected_samples = request.args.getlist("samples")

    bad_qc_actions = [member.value for member in BadSampleQualityAction]
    return render_template(
        "group.html",
        title=group_id,
        group_name=group_info["display_name"],
        bad_qc_actions=bad_qc_actions,
        selected_samples=selected_samples,
        group_desc=group_info["description"],
        samples=samples["records"],
        modified=group_info["modified_at"],
        table_definition=table_definition,
    )


@groups_bp.route("/groups/qc_status", methods=["POST"])
@login_required
def update_qc_classification():
    """Update the quality control report of one or more samples.

    Redirects back to groups.groups and preserves table selection
    """

    selected_samples = request.form.getlist("qc-selected-samples")

    LOG.debug("Processing request to set QC for %s", selected_samples)

    if not selected_samples:
        LOG.warning("Received request to set QC but no selected samples")
        flash(
            "No samples selected for QC status update. Please choose at least one sample.",
            "warning",
        )

    token = TokenObject(**current_user.get_id())

    # build data to store in db
    result = request.form.get("qc-validation", None)
    if result == QualityControlResult.PASSED.value:
        action = None
        comment = ""
    elif result == QualityControlResult.FAILED.value:
        comment = request.form.get("qc-comment", "")
        action = request.form.get("qc-action", "")
    else:
        raise ValueError(f"Unknown value of qc classification, {result}")

    for sample_id in selected_samples:
        try:
            update_sample_qc_classification(
                token,
                sample_id=sample_id,
                status=result,
                action=action,
                comment=comment,
            )
        except Exception as error:
            LOG.exception(
                "Encountered error when updating QC status for sample %s:", sample_id
            )
            flash(str(error), "danger")

    # return redirect(url_for("groups.groups", samples=selected_samples))
    # add sample ids as params to referrer url
    url = urlparse(request.referrer)
    sample_id_param = "&".join([f"samples={sid}" for sid in selected_samples])
    upd_url = url._replace(query=sample_id_param).geturl()
    return redirect(upd_url)
