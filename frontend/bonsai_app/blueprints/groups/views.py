"""Declaration of views for groups"""

import json
import logging
from urllib.parse import urlparse

from bonsai_libs.api_client.bonsai.models import CreateGroupInput
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from pydantic import ValidationError
from requests.exceptions import HTTPError

from bonsai_app.config import settings
from bonsai_app.bonsai_api import get_api_client
from bonsai_app.models import (
    BadSampleQualityAction,
    PhenotypeType,
    QualityControlResult,
)

from .controller import build_updated_presets, format_tablular_data

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

    client = get_api_client()
    samples_info = client.get_sample_summaries(limit=0, offset=0)

    bad_qc_actions = [member.value for member in BadSampleQualityAction]

    # generate table data
    manifest = client.get_valid_summary_columns()
    table_data = format_tablular_data(samples_info["data"], manifest["columns"])

    return render_template(
        "groups.html",
        title="Groups",
        table_data=table_data,
        token=current_user.token,
        bad_qc_actions=bad_qc_actions,
    )


@groups_bp.route("/groups/create", methods=["GET"])
@groups_bp.route("/groups/<group_id>/edit", methods=["GET"])
@login_required
def group_editor_view(group_id: str | None = None):
    client = get_api_client()
    groups = client.get_groups()

    return render_template(
        "edit_groups.html",
        mode="create" if group_id is None else "edit",
        group_id=group_id,
        groups=groups,
        api_base_url=settings.api_external_url,
        access_token=current_user.token,
        refresh_token="",
    )


@groups_bp.route("/groups/edit_old", methods=["GET", "POST"])
@groups_bp.route("/groups/edit_old/<group_id>", methods=["GET", "POST"])
@login_required
def edit_groups_old(group_id: str | None = None):
    """Generate edit groups view

    :param group_id: Group id, defaults to None
    :type group_id: str, optional
    :return: generated HTML page
    :rtype: str
    """
    # if not valid token or if user is not admin
    if current_user.get_id() is None or not current_user.is_admin:
        return redirect(url_for("public.index"))

    client = get_api_client()
    all_groups = client.get_groups()

    # remove group from database
    if request.method == "POST":
        # if a group should be removed
        if "input-remove-group" in request.form:
            try:
                client.delete_group(group_id=request.form.get("input-remove-group"))
                flash("Group updated", "success")
            except HTTPError as err:
                flash(f"An error occurred when updating group, {err}", "danger")
            return redirect(url_for("groups.group_editor_view"))
        elif "input-update-group" in request.form:
            updated_data = json.loads(request.form.get("input-update-group"))
            try:
                client.update_group_core_info(
                    group_id=group_id,
                    name=updated_data.get("display_name", None),
                    description=updated_data.get("description", None),
                )
                preset = build_updated_presets(updated_data)
                client.update_group_presets(
                    group_id=group_id, set_default=True, preset=preset
                )
                flash("Group updated", "success")
                return redirect(url_for("groups.group_editor_view", group_id=group_id))
            except HTTPError as err:
                flash(f"An error occurred when updating group, {err}", "danger")
        elif "input-create-group" in request.form:
            raw_data = json.loads(request.form.get("input-create-group", {}))
            try:
                # cast as input object
                input_data = CreateGroupInput.model_validate(raw_data)

                client.create_group(data=input_data.group_id)
                flash("Group updated", "success")
                return redirect(url_for("groups.group_editor_view", group_id=group_id))
            except HTTPError as err:
                flash(f"An error occurred when updating group, {err}", "danger")
            except ValidationError as err:
                LOG.error("Invalid group format: %s", err)
                flash(f"An error occurred when updating group, {err}", "danger")

    # get valid phenotypes
    valid_phenotypes = {
        entry.name.lower().capitalize().replace("_", " "): entry.value
        for entry in PhenotypeType.__members__.values()
    }

    # annotate if column previously have been selected
    if group_id is not None:
        columns = client.get_valid_group_columns(
            group_id=group_id, include_invisible=True
        )
    else:
        manifest_cols = client.get_valid_summary_columns()
        columns = manifest_cols["columns"]

    valid_cols_idx = {col["id"]: col for col in columns}
    return render_template(
        "edit_groups.html",
        title="Groups",
        selected_group=group_id,
        groups=all_groups["data"],
        valid_columns=list(valid_cols_idx.values()),
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
    # check if qc metrics should be displayed
    display_qc: bool = request.args.get(
        "qc", False, type=lambda val: val.lower() == "true"
    )

    # query API for sample info
    client = get_api_client()
    try:
        samples_info = client.get_sample_summaries(group_id=group_id)
        # get column definition to use
        group_info = client.get_group(group_id=group_id)
    except HTTPError as error:
        # throw proper error page
        abort(error.response.status_code)

    # Pre-select samples in sample table:
    selected_samples = request.args.getlist("samples")

    bad_qc_actions = [member.value for member in BadSampleQualityAction]

    # generate table data
    if column_info := (group_info.table_columns and len(column_info) > 0):
        column_info = client.get_valid_group_columns(group_id=group_id)
    else:  # get default columns
        column_info = client.get_valid_summary_columns()
    table_data = format_tablular_data(samples_info["data"], column_info["columns"])

    # indicate view in title, used for testing
    title = f"Group - {group_id}"
    if display_qc:
        title += " - QC results"
    return render_template(
        "group.html",
        title=title,
        group_id=group_id,
        group_name=group_info.display_name,
        bad_qc_actions=bad_qc_actions,
        selected_samples=selected_samples,
        group_desc=group_info.description,
        table_data=table_data,
        table_definition=group_info.table_columns,
        modified=group_info.modified_at,
        display_qc=display_qc,
        token=current_user.token,
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

    client = get_api_client()

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
            client.update_sample_qc_classification(
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

    # add sample ids as params to referrer url
    url = urlparse(request.referrer)
    sample_id_param = "&".join([f"samples={sid}" for sid in selected_samples])
    upd_url = url._replace(query=sample_id_param).geturl()
    return redirect(upd_url)
