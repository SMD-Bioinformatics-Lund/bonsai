"""Declaration of views for samples"""

import json
import logging
from datetime import date
from itertools import groupby
from typing import Any, Dict, Tuple

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from requests import HTTPError

from bonsai_app.bonsai import (
    TokenObject,
    cgmlst_cluster_samples,
    create_curation,
    delete_samples,
    find_samples_similar_to_reference,
    get_antibiotics,
    get_lims_export_response,
    get_sample_by_id,
    get_variant_rejection_reasons,
    post_comment_to_sample,
    remove_comment_from_sample,
    update_sample_qc_classification,
    update_variant_info,
)
from bonsai_app.models import BadSampleQualityAction, QualityControlResult
from .controllers import (
    build_curation_records,
    filter_variants,
    filter_variants_if_processed,
    get_all_variant_types,
    get_all_who_classifications,
    get_results_by,
    get_variant_genes,
    kw_metadata_to_table,
    sort_variants,
    split_metadata,
    submit_curations_batch,
)

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
    sample_info = filter_variants_if_processed(sample_info)
    
    # Sort variants within all prediction results
    for pred_res in sample_info.get("element_type_result", []):
        if "variants" in pred_res.get("result", {}):
            pred_res["result"]["variants"] = sort_variants(
                pred_res["result"]["variants"]
            )

    # get all actions if sample fail qc
    bad_qc_actions = [member.value for member in BadSampleQualityAction]

    kw_meta_records, meta_tbls = split_metadata(sample_info)

    return render_template(
        "sample.html",
        sample=sample_info,
        group_id=group_id,
        title=sample_info['sample_name'],
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
        status_code = error.response.status_code
        status = error.response.status_code == 401
        if status:
            current_app.logger.warning(
                "LIMS export error - no permissoin %s", current_user.username
            )
            flash("You dont have permission to export the result to LIMS", "warning")
        elif status_code == 404:
            flash("Sample not found", "warning")
        elif status_code == 422:
            default_msg = "Export is not supported for this assay"
            flash(error.response.json().get("detail", default_msg), "warning")
        elif status_code == 501:
            flash("Export not implemented for this assay", "warning")
        else:
            current_app.logger.error(
                "LIMS export error - generic error: %s", error.response
            )
            flash("Error when generating export file", "warning")
        return redirect(request.referrer)

    # build Flask response using the API headers and bytes
    content = api_resp.content  # bytes
    response = make_response(content)

    # Forward content type if provided
    content_type = api_resp.headers.get("Content-Type")
    if content_type:
        response.headers["Content-Type"] = content_type
    else:
        # fallback based on format
        response.headers["Content-Type"] = (
            "text/tab-separated-values; charset=utf-8"
            if fmt == "tsv"
            else "text/csv; charset=utf-8"
        )
    # Forward filename if provided; else build default one
    dispo = api_resp.headers.get("Content-Disposition")
    if not dispo:
        response.headers["Content-Disposition"] = (
            f"attachment; filename={fallback_fname}.txt"
        )
    else:
        response.headers["Content-Disposition"] = dispo
    # Saftey
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    return response


@samples_bp.route("/sample/<sample_id>/resistance/variants", methods=["GET", "POST"])
@login_required
def resistance_variants(sample_id: str) -> str:
    """Display and manage resistance variants for a sample.

    Supports filtering and classification of variants from tbprofiler AMR analysis.

    :param sample_id: The sample identifier
    :type sample_id: str
    :return: Rendered HTML page
    :rtype: str
    """
    token = TokenObject(**current_user.get_id())
    sample_info = get_sample_by_id(token, sample_id=sample_id)

    # Handle POST requests for filtering or variant classification
    if request.method == "POST":
        if "classify-variant" in request.form:
            try:
                records = json.loads(request.form.get("curations", "[]"))
                resistance = request.form.getlist("amrs")

                if len(records) == 0:
                    flash("No variants selected for curation", "info")
                    return redirect(url_for("samples.resistance_variants", sample_id=sample_id))
                
                # resolve rejection reason
                rej_reason = None
                if request.form.get("verify-variant-btn") == "failed":
                    rej_reason_label = request.form.get("rejection-reason")
                    rejection_reasons = get_variant_rejection_reasons()
                    rej_reason = next(
                        (r for r in rejection_reasons 
                         if r["label"] == rej_reason_label),
                        None
                    )
                    if not rej_reason:
                        flash("Invalid rejection reason", "danger")
                        return redirect(url_for("samples.resistance_variants",
                                               sample_id=sample_id))
                    
                # Build and submit curations
                batch_records = build_curation_records(
                    records=records,
                    decision=request.form.get("verify-variant-btn"),
                    rejection_reason=rej_reason,
                    phenotypes=resistance,
                )
                results = submit_curations_batch(token, batch_records)
            
                # Report results to user
                successes = sum(1 for r in results if r.success)
                failures = sum(1 for r in results if not r.success)
                
                if successes > 0:
                    flash(f"Successfully created {successes} curation(s)", "success")
                if failures > 0:
                    error_details = "; ".join(r.error for r in results if not r.success)
                    flash(f"Failed to create {failures} curation(s): {error_details}", 
                          "danger")

            except (json.JSONDecodeError, ValueError) as err:
                LOG.error("Invalid form data: %s", err)
                flash("Invalid form data submitted", "danger")
            # except Exception as err:
            #     LOG.error("Unexpected error processing curations: %s", err)
            #     flash("An unexpected error occurred", "danger")
            
        else:
            # Apply variant filters from form
            sample_info = filter_variants(sample_info, form=request.form)

    # Sort variants within all tbprofiler AMR results
    tbprofiler_results = get_results_by(
        sample_info, software="tbprofiler", analysis_type="amr"
    )
    for pred_res in tbprofiler_results:
        pred_res["result"]["variants"] = sort_variants(
            pred_res["result"]["variants"]
        )

    # Sort top-level structural and SNV variants if present
    for variant_key in ("sv_variants", "snv_variants"):
        if variant_key in sample_info and sample_info[variant_key]:
            sample_info[variant_key] = sort_variants(sample_info[variant_key])

    # Check if IGV genome browser should be enabled
    display_genome_browser = all(
        [
            sample_info.get("reference_genome") is not None,
            sample_info.get("read_mapping") is not None,
        ]
    )

    # Prepare antibiotics grouped by family for filter form
    antibiotics = {
        fam: list(amrs)
        for fam, amrs in groupby(get_antibiotics(), key=lambda ant: ant["family"])
    }
    
    # Get rejection reasons for form
    rejection_reasons = get_variant_rejection_reasons()

    # Prepare filter form data
    form_data = {
        "filter_genes": get_variant_genes(sample_info, software="tbprofiler"),
        "filter_who_class": get_all_who_classifications(
            sample_info, software="tbprofiler"
        ),
        "filter_variant_type": get_all_variant_types(
            sample_info, software="tbprofiler"
        ),
    }

    # Filter AMR results to only display tbprofiler non-virulence results
    amr_results = [
        elem for elem in sample_info.get("element_type_result", [])
        if elem.get("software") == "tbprofiler" and elem.get("type") != "VIRULENCE"
    ]

    # Prepare form state with user selections
    form_state = {
        "freq_operator": request.form.get("freq-operator", "gte"),
        "min_frequency": request.form.get("min-frequency", ""),
        "depth_operator": request.form.get("depth-operator", "gte"),
        "min_depth": request.form.get("min-depth", ""),
        "selected_genes": set(request.form.getlist("filter-genes")),
        "selected_types": set(request.form.getlist("filter-variant-type")),
        "selected_who_classes": set(request.form.getlist("filter-who-class")),
        "yield_resistance": bool(request.form.get("yeild-resistance")),
        "hide_dismissed": bool(request.form.get("hide-dismissed")),
    }

    # Enhance structural variants with computed data
    for variant in sample_info.get("sv_variants", []):
        # Determine row styling based on verification status
        variant["row_class"] = (
            "table-success" if variant.get("verified") == "passed"
            else "table-danger" if variant.get("verified") == "failed"
            else ""
        )
        # Prepare display ID for IGV links
        variant["display_id"] = f"sv_variants-{variant.get('id', '')}"

    # Split metadata into key-value and table formats
    _, meta_tbls = split_metadata(sample_info)

    return render_template(
        "resistance_variants.html",
        title=f"{sample_id} resistance",
        sample=sample_info,
        amr_results=amr_results,
        form_data=form_data,
        form_state=form_state,
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
