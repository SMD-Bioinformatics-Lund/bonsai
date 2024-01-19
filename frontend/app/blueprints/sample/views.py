"""Declaration of views for samples"""
import json
from typing import Any, Dict, Tuple

from app.bonsai import (
    TokenObject,
    cgmlst_cluster_samples,
    delete_samples,
    find_and_cluster_similar_samples,
    find_samples_similar_to_reference,
    get_group_by_id,
    get_sample_by_id,
    post_comment_to_sample,
    remove_comment_from_sample,
    update_sample_qc_classification,
)
from app.models import BadSampleQualityAction, QualityControlResult
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from requests.exceptions import HTTPError

from .controllers import create_amr_summary

samples_bp = Blueprint(
    "samples",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/samples/static",
)


@samples_bp.route("/samples")
@login_required
def samples():
    """Samples view."""
    return render_template("samples.html")


@samples_bp.route("/samples/remove", methods=["POST"])
@login_required
def remove_samples():
    """Remove samples."""
    if current_user.is_admin:
        token = TokenObject(**current_user.get_id())

        sample_ids = json.loads(request.form.get("sample-ids", "[]"))
        if len(sample_ids) > 0:
            delete_samples(token, sample_ids=sample_ids)
    else:
        flash("You dont have permission to remove samples", "warning")
    return redirect(request.referrer)


@samples_bp.route("/samples/cluster/", methods=["GET", "POST"])
@login_required
def cluster(sample_id: str) -> str:
    """Samples view."""
    token = TokenObject(**current_user.get_id())

    if request.method == "POST":
        samples_info = request.body["samples"]
        cgmlst_cluster_samples(token, samples=samples_info)
    return render_template("sample.html", sample_id=sample_id)


@samples_bp.route("/sample/<sample_id>")
@login_required
def sample(sample_id: str) -> str:
    """Generate sample page.

    :param sample_id: Sample id
    :type sample_id: str
    :raises ValueError: _description_
    :raises ValueError: _description_
    :return: Rendered HTML page
    :rtype: str
    """
    config = current_app.config
    current_app.logger.debug("Removing non-validated genes from input")
    token = TokenObject(**current_user.get_id())
    # get sample
    try:
        sample_info = get_sample_by_id(token, sample_id=sample_id)
    except HTTPError as error:
        # throw proper error page
        abort(error.response.status_code)

    # if verbose output should be rendered
    extended = bool(request.args.get("extended", False))

    # if a sample was accessed from a group it can pass the group_id as parameter
    # group_id is used to fetch information on validated genes and resitances
    group_id = request.args.get("group_id")
    if group_id:
        get_group_by_id(token, group_id=group_id)
        # validated_genes = group.get("validatedGenes", {})

    # summarize predicted antimicrobial resistance
    # amr_summary, resistance_info = create_amr_summary(sample_info)

    # sort phenotypic predictions so Tb is first
    order = {"tbprofiler": 10, "mykrobe": 1}
    sample_info["element_type_result"] = sorted(
        sample_info["element_type_result"],
        key=lambda res: order.get(res["software"], 0),
        reverse=True,
    )

    # get all actions if sample fail qc
    bad_qc_actions = [member.value for member in BadSampleQualityAction]

    # Get the most similar samples and calculate the pair-wise similaity
    typing_method = config["SAMPLE_VIEW_TYPING_METHOD"]
    job = find_and_cluster_similar_samples(
        token,
        sample_id=sample_id,
        limit=config["SAMPLE_VIEW_SIMILARITY_LIMIT"],
        similarity=config["SAMPLE_VIEW_SIMILARITY_THRESHOLD"],
        typing_method=typing_method,
        cluster_method=config["SAMPLE_VIEW_CLUSTER_METHOD"],
    )
    simiar_samples = {"job": job.model_dump(), "typing_method": typing_method}

    return render_template(
        "sample.html",
        sample=sample_info,
        title=sample_id,
        is_filtered=bool(group_id),
        similar_samples=simiar_samples,
        bad_qc_actions=bad_qc_actions,
        extended=extended,
    )


@samples_bp.route("/sample/<sample_id>/similar", methods=["POST"])
@login_required
def find_similar_samples(sample_id: str) -> Tuple[Dict[str, Any], int]:
    """Find samples that are similar."""
    token = TokenObject(**current_user.get_id())
    limit = request.json.get("limit", 10)
    similarity = request.json.get("similarity", 0.5)
    try:
        resp = find_samples_similar_to_reference(
            token, sample_id=sample_id, limit=limit, similarity=similarity
        )
    except HTTPError as error:
        return {"status": 500, "details": str(error)}, 500
    return resp.model_dump(), 200


@samples_bp.route("/sample/<sample_id>/comment", methods=["POST"])
@login_required
def add_comment(sample_id: str) -> str:
    """Post sample."""
    token = TokenObject(**current_user.get_id())
    # post comment
    data = request.form["comment"]
    try:
        post_comment_to_sample(
            token, sample_id=sample_id, user_name=current_user.username, comment=data
        )
    except HTTPError:
        flash("Error posting commment", "danger")
    return redirect(url_for("samples.sample", sample_id=sample_id))


@samples_bp.route("/sample/<sample_id>/comment/<comment_id>", methods=["POST"])
@login_required
def hide_comment(sample_id: str, comment_id: str) -> str:
    """Hist comment for sample."""
    token = TokenObject(**current_user.get_id())
    # hide comment
    try:
        remove_comment_from_sample(token, sample_id=sample_id, comment_id=comment_id)
    except HTTPError as error:
        flash(str(error), "danger")
    return redirect(url_for("samples.sample", sample_id=sample_id))


@samples_bp.route("/sample/<sample_id>/qc_status", methods=["POST"])
@login_required
def update_qc_classification(sample_id: str) -> str:
    """Update the quality control report of a sample."""
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

    try:
        update_sample_qc_classification(
            token, sample_id=sample_id, status=result, action=action, comment=comment
        )
    except HTTPError as error:
        flash(str(error), "danger")
    return redirect(url_for("samples.sample", sample_id=sample_id))


@samples_bp.route("/sample/<sample_id>/resistance_report")
@login_required
def resistance_report(sample_id: str) -> str:
    """Samples view."""
    token = TokenObject(**current_user.get_id())
    sample_info = get_sample_by_id(token, sample_id=sample_id)
    return render_template(
        "resistance_report.html", title=f"{sample_id} resistance", sample=sample_info
    )
