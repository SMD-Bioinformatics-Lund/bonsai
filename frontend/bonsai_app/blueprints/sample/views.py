"""Declaration of views for samples"""

import json
import logging
from datetime import date
from itertools import groupby
from typing import Any, Dict, Tuple

from flask import (Blueprint, abort, current_app, flash, make_response,
                   redirect, render_template, request, url_for)
from flask_login import current_user, login_required
from requests import HTTPError

from ...bonsai import (
    TokenObject,
    cgmlst_cluster_samples,
    delete_samples,
    find_samples_similar_to_reference,
    get_antibiotics,
    get_group_by_id,
    get_lims_export_response,
    get_sample_by_id,
    get_variant_rejection_reasons,
    post_comment_to_sample,
    remove_comment_from_sample,
    update_sample_qc_classification,
    update_variant_info,
)
from ...models import BadSampleQualityAction, QualityControlResult
from .controllers import (filter_variants, filter_variants_if_processed,
                          get_all_variant_types, get_all_who_classifications,
                          get_variant_genes, kw_metadata_to_table,
                          sort_variants, split_metadata)

LOG = logging.getLogger(__name__)

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
            result = delete_samples(token, sample_ids=sample_ids)
            current_app.logger.info(
                "removed %d samples, removed from %d groups",
                result["n_deleted"],
                result["removed_from_n_groups"],
            )
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
    group_id: str | None = request.args.get("group_id")

    # sort phenotypic predictions so Tb is first
    order = {"tbprofiler": 10, "mykrobe": 1}
    sample_info["element_type_result"] = sorted(
        sample_info["element_type_result"],
        key=lambda res: order.get(res["software"], 0),
        reverse=True,
    )

    # filter tbprofiler results and sort variants
    LOG.warning(len(sample_info["element_type_result"][0]["result"]["variants"]))
    sample_info = filter_variants_if_processed(sample_info)
    LOG.warning(len(sample_info["element_type_result"][0]["result"]["variants"]))
    sample_info = sort_variants(sample_info)
    LOG.warning(len(sample_info["element_type_result"][0]["result"]["variants"]))

    # get all actions if sample fail qc
    bad_qc_actions = [member.value for member in BadSampleQualityAction]

    kw_meta_records, meta_tbls = split_metadata(sample_info)

    return render_template(
        "sample.html",
        sample=sample_info,
        group_id=group_id,
        title=sample_id,
        is_filtered=bool(group_id),
        bad_qc_actions=bad_qc_actions,
        extended=extended,
        kw_metadata=kw_meta_records,
        metadata_tbls=meta_tbls,
        token=token.token,
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


@samples_bp.route(
    "/sample/<sample_id>/resistance/variants/download", methods=["GET", "POST"]
)
@login_required
def download_lims(sample_id: str):
    """Download a LIMS compatible file with UTF-8 encoding."""
    # get user auth token
    token = TokenObject(**current_user.get_id())

    # default file name
    fmt = request.args.get("fmt", "tsv")
    today = date.today()
    fallback_fname = request.args.get(
        "filename", f"bonsai-lims-export_{sample_id}_{today.isoformat()}"
    )

    # Fetch from API
    try:
        api_resp = get_lims_export_response(token, sample_id=sample_id, fmt=fmt)
    except HTTPError as error:
        # log errors
        status = error.response.status_code == 401
        if status:
            current_app.logger.warning(
                "LIMS export error - no permissoin %s", current_user.username
            )
            flash("You dont have permission to export the result to LIMS", "warning")
        elif status == 404:
            flash("Sample not found", "warning")
        elif status == 422:
            flash("Export is not supported for this assay", "warning")
        elif status == 501:
            flash("Export not implemented for this assay", "warning")
        else:
            current_app.logger.error(
                "LIMS export error - generic error: %s", error.response
            )
            flash("Error when generating export file", "warning")
        return redirect(request.referrer)

    # build Flask response using the API headers and bytes
    content = api_resp.content # bytes
    response = make_response(content)

    # Forward content type if provided
    content_type = api_resp.headers.get("Content-Type")
    if content_type:
        response.headers["Content-Type"] = content_type
    else:
        # fallback based on format
        response.headers["Content-Type"] = (
            "text/tab-separated-values; charset=utf-8" if fmt == "tsv" else "text/csv; charset=utf-8"
        )
    # Forward filename if provided; else build default one
    dispo = api_resp.headers.get("Content-Disposition")
    if not dispo:
        response.headers["Content-Disposition"] = f"attachment; filename={fallback_fname}.txt"
    else:
        response.headers["Content-Disposition"] = dispo
    # Saftey
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    return response


@samples_bp.route("/sample/<sample_id>/resistance/variants", methods=["GET", "POST"])
@login_required
def resistance_variants(sample_id: str) -> str:
    """Samples view."""
    token = TokenObject(**current_user.get_id())
    sample_info = get_sample_by_id(token, sample_id=sample_id)
    sample_info = sort_variants(sample_info)

    # check if IGV should be enabled
    display_genome_browser = all(
        [
            sample_info["reference_genome"] is not None,
            sample_info["read_mapping"] is not None,
        ]
    )

    # populate form for filter varaints
    antibiotics = {
        fam: list(amrs)
        for fam, amrs in groupby(get_antibiotics(), key=lambda ant: ant["family"])
    }
    rejection_reasons = get_variant_rejection_reasons()

    # populate form for filter varaints
    form_data = {
        "filter_genes": get_variant_genes(sample_info, software="tbprofiler"),
        "filter_who_class": get_all_who_classifications(
            sample_info, software="tbprofiler"
        ),
        "filter_variant_type": get_all_variant_types(
            sample_info, software="tbprofiler"
        ),
    }

    if request.method == "POST":
        # check if which form deposited data
        if "classify-variant" in request.form:
            token = TokenObject(**current_user.get_id())
            variant_ids = json.loads(request.form.get("variant-ids", "[]"))
            resistance: list[str] = request.form.getlist("amrs")
            # expand rejection reason label to full db object
            rej_reason = None
            for reason in rejection_reasons:
                if reason["label"] == request.form.get("rejection-reason"):
                    rej_reason = reason
            # parse updated variant classification
            status: dict[str, str | list[str] | None] = {
                "verified": request.form.get("verify-variant-btn"),
                "reason": rej_reason,
                "phenotypes": resistance,
                "resistance_lvl": request.form.get("resistance-lvl-btn"),
            }
            sample_info = update_variant_info(
                token, sample_id=sample_id, variant_ids=variant_ids, status=status
            )
        else:
            sample_info = filter_variants(sample_info, form=request.form)
        # resort variants after processing
        sample_info = sort_variants(sample_info)

    _, meta_tbls = split_metadata(sample_info)

    return render_template(
        "resistance_variants.html",
        title=f"{sample_id} resistance",
        sample=sample_info,
        form_data=form_data,
        antibiotics=antibiotics,
        rejection_reasons=rejection_reasons,
        display_igv=display_genome_browser,
        metadata_tbls=meta_tbls,
    )


@samples_bp.route("/sample/<sample_id>/metadata", methods=["GET", "POST"])
@login_required
def metadata(sample_id: str) -> str:
    """Open a metadata table."""

    token = TokenObject(**current_user.get_id())
    # get sample
    try:
        sample_info = get_sample_by_id(token, sample_id=sample_id)
    except HTTPError as error:
        # throw proper error page
        abort(error.response.status_code)

    kw_metadata, metadata_tbls = split_metadata(sample_info)
    kw_tbl = kw_metadata_to_table(kw_metadata)
    grouped_meta_tbl = {
        name: list(gr)
        for name, gr in groupby(metadata_tbls, key=lambda x: x["category"])
    }

    return render_template(
        "metadata.html",
        title=f"{sample_id} metadata",
        sample=sample_info,
        kw_tbl=kw_tbl,
        metadata_tbls=metadata_tbls,
        grouped_metadata_tbls=grouped_meta_tbl,
    )


@samples_bp.route("/sample/<sample_id>/metadata/<fieldname>", methods=["GET", "POST"])
@login_required
def open_metadata_tbl(sample_id: str, fieldname: str) -> str:
    """Open a metadata table."""

    token = TokenObject(**current_user.get_id())
    # get sample
    try:
        sample_info = get_sample_by_id(token, sample_id=sample_id)
    except HTTPError as error:
        # throw proper error page
        abort(error.response.status_code)

    _, metadata_tbls = split_metadata(sample_info)
    indexed_tbls = {tbl["fieldname"]: tbl for tbl in metadata_tbls}
    table = indexed_tbls.get(fieldname, None)

    return render_template(
        "metadata_table.html",
        title=f"{sample_id} metadata",
        sample=sample_info,
        table=table,
    )
