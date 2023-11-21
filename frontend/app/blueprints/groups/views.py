"""Declaration of views for groups"""
import json
import logging

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from requests.exceptions import HTTPError

from app.bonsai import (
    TokenObject,
    create_group,
    delete_group,
    get_groups,
    get_samples,
    get_samples_by_id,
    get_samples_in_group,
    update_group,
    update_sample_qc_classification,
)
from app.models import PhenotypeType, BadSampleQualityAction, QualityControlResult

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
    selected_samples = request.args.getlist("samples")

    current_app.logger.debug(selected_samples)

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
        match request.form:
            case "input-remove-group":
                try:
                    delete_group(token, group_id=request.form.get("input-remove-group"))
                    flash("Group updated", "success")
                except HTTPError as err:
                    flash(f"An error occured when updating group, {err}", "danger")
                return redirect(url_for("groups.edit_groups"))
            case "input-update-group":
                updated_data = json.loads(request.form.get("input-update-group"))
                try:
                    update_group(token, group_id=group_id, data=updated_data)
                    flash("Group updated", "success")
                    return redirect(url_for("groups.edit_groups"))
                except HTTPError as err:
                    flash(f"An error occured when updating group, {err}", "danger")
            case "input-create-group":
                input_data = json.loads(request.form.get("input-create-group", {}))
                try:
                    create_group(token, data=input_data)
                    flash("Group updated", "success")
                    return redirect(url_for("groups.edit_groups"))
                except HTTPError as err:
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
        groups=all_groups,
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
    group_info = get_samples_in_group(token, group_id=group_id, lookup_samples=False)
    table_definition = group_info["table_columns"]
    samples = get_samples_by_id(
        token, limit=0, skip=0, sample_ids=group_info["included_samples"]
    )
    return render_template(
        "group.html",
        title=group_id,
        group_name=group_info["display_name"],
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

    current_app.logger.debug("Processing request to set QC for %s", selected_samples)

    if not selected_samples:
        current_app.logger.warning("Received request to set QC but no selected samples")
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
            current_app.logger.exception(
                "Encountered error when updating QC status for sample %s", sample_id
            )
            flash(str(error), "danger")

    return redirect(url_for("groups.groups", samples=selected_samples))
