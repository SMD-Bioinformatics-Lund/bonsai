"""Declaration of views for samples"""
from itertools import chain, groupby
from requests.exceptions import HTTPError

from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app
from flask_login import current_user, login_required

from app.bonsai import (TokenObject, cgmlst_cluster_samples,
                        find_samples_similar_to_reference, find_and_cluster_similar_samples, 
                        get_group_by_id, get_sample_by_id, 
                        post_comment_to_sample, remove_comment_from_sample,
                        update_sample_qc_classification)
from app.models import (NT_TO_AA, BadSampleQualityAction, ElementType,
                        PredictionSoftware)

samples_bp = Blueprint(
    "samples",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/samples/static",
)


def _has_phenotype(feature, phenotypes) -> bool:
    """Check if gene or mutation has phenotype."""
    phenotypes = [phe.lower() for phe in phenotypes]
    return any(pheno.lower() in phenotypes for pheno in feature["phenotypes"])


@samples_bp.route("/samples")
@login_required
def samples():
    """Samples view."""
    return render_template("samples.html")


@samples_bp.route("/samples/<sample_id>")
@login_required
def sample(sample_id):
    """Samples view."""
    config = current_app.config
    current_app.logger.debug('Removing non-validated genes from input')
    token = TokenObject(**current_user.get_id())
    # get sample
    sample = get_sample_by_id(token, sample_id=sample_id)

    # if a sample was accessed from a group it can pass the group_id as parameter
    # group_id is used to fetch information on validated genes and resitances
    group_id = request.args.get("group_id")
    if group_id:
        group = get_group_by_id(token, group_id=group_id)
        validated_genes = group.get("validatedGenes", {})
        # remove non validated genes from output
        for category, valid_genes in validated_genes.items():
            current_app.logger.debug('Removing non-validated genes from input')
            pred_res = next(
                iter([r for r in sample["phenotypeResult"] if r["type"] == category])
            )
            # filter genes based on the list of validated genes/ phenotypes for group
            if category.endswith("resistance"):
                filtered_genes = [
                    res
                    for res in pred_res["result"]["genes"]
                    if _has_phenotype(res, valid_genes)
                ]
                filtered_mutations = [
                    res
                    for res in pred_res["result"]["mutations"]
                    if _has_phenotype(res, valid_genes)
                ]
                resistance = {
                    phe
                    for feat in chain(filtered_genes, filtered_mutations)
                    for phe in feat["phenotypes"]
                }
                # update phenotypes
                pred_res["result"]["phenotypes"] = {
                    "resistant": list(resistance),
                    "susceptible": list(set(validated_genes) - resistance),
                }
                pred_res["result"]["genes"] = filtered_genes
                pred_res["result"]["mutations"] = filtered_mutations
            else:
                genes = [
                    gene
                    for gene in pred_res["result"].get("genes", [])
                    if gene["name"] in valid_genes
                ]
                mutations = [
                    mut
                    for mut in pred_res["result"].get("mutations", [])
                    if mut["genes"] in valid_genes
                ]
                # update object from database
                pred_res["result"]["genes"] = genes
                pred_res["result"]["mutations"] = mutations

    # summarize predicted antimicrobial resistance
    amr_summary = {}
    resistance_info = {"genes": {}, "mutations": {}}
    current_app.logger.debug('Make AMR prediction summary table')
    for pred_res in sample["element_type_result"]:
        # only get AMR resistance
        if pred_res["type"] == ElementType.AMR.value:
            for gene in pred_res["result"]["genes"]:
                gene_name = gene["gene_symbol"]
                if gene_name is None:
                    raise ValueError()
                # get/create summary dictionary object
                gene_entry = amr_summary.get(
                    gene_name,
                    {
                        # create default object
                        "gene_symbol": gene_name,
                        "software": [],
                        "res_class": "Unknown",
                    },
                )
                # annotate softwares
                gene_entry["software"].append(pred_res["software"])

                # annotate resistance class
                if pred_res["software"] == PredictionSoftware.AMRFINDER.value:
                    gene_entry["res_class"] = gene["res_class"]

                # store object
                amr_summary[gene_name] = gene_entry

                # reformat resistance gene table
                gene_entry = resistance_info["genes"].get(gene_name, [])
                gene["software"] = pred_res["software"]
                gene_entry.append(gene)
                resistance_info["genes"][gene_name] = gene_entry

            # iterate over mutations and populate resistance summaries
            for mutation in pred_res["result"]["mutations"]:
                gene_name, *_ = mutation["ref_id"].split(";;")
                # gene entries
                gene_entry = amr_summary.get(
                    gene_name,
                    {
                        # create default object
                        "gene_symbol": gene_name,
                        "software": [],
                        "res_class": "Unknown",
                    },
                )
                if mutation["variant_type"] == "substitution":
                    ref_aa = NT_TO_AA[mutation["ref_codon"].upper()]
                    alt_aa = NT_TO_AA[mutation["alt_codon"].upper()]
                    gene_entry["change"] = f"{ref_aa}{mutation['position']}{alt_aa}"
                else:
                    raise ValueError()
                # store object
                amr_summary[gene_name] = gene_entry

    # group summary by res_class
    amr_summary = {
        res_type: list(rows)
        for res_type, rows in groupby(
            amr_summary.values(), key=lambda x: x["res_class"]
        )
    }
    # get all actions if sample fail qc
    bad_qc_actions = [member.value for member in BadSampleQualityAction]

    # Get the most similar samples and calculate the pair-wise similaity
    typing_method = config["SAMPLE_VIEW_TYPING_METHOD"]
    job = find_and_cluster_similar_samples(
        token, sample_id=sample_id, 
        limit=config["SAMPLE_VIEW_SIMILARITY_LIMIT"], 
        similarity=config["SAMPLE_VIEW_SIMILARITY_THRESHOLD"],
        typing_method=typing_method,
        cluster_method=config["SAMPLE_VIEW_CLUSTER_METHOD"]
    )
    simiar_samples = {"job": job.model_dump(), "typing_method": typing_method}

    return render_template(
        "sample.html",
        sample=sample,
        amr_summary=amr_summary,
        resistance_info=resistance_info,
        title=sample_id,
        is_filtered=bool(group_id),
        similar_samples=simiar_samples,
        bad_qc_actions=bad_qc_actions,
    )


@samples_bp.route("/samples/<sample_id>/similar", methods=["POST"])
@login_required
def find_similar_samples(sample_id):
    """Find samples that are similar."""
    token = TokenObject(**current_user.get_id())
    limit = request.json.get("limit", 10)
    similarity = request.json.get("similarity", 0.5)
    try:
        resp = find_samples_similar_to_reference(
            token, sample_id=sample_id, limit=limit, similarity=similarity
        )
    except Exception as error:
        return {"status": 500, "details": str(error)}, 500
    return resp.model_dump(), 200


@samples_bp.route("/samples/<sample_id>/comment", methods=["POST"])
@login_required
def add_comment(sample_id):
    """Post sample."""
    token = TokenObject(**current_user.get_id())
    # post comment
    data = request.form["comment"]
    # todo validate data
    try:
        resp = post_comment_to_sample(
            token, sample_id=sample_id, user_name=current_user.username, comment=data
        )
    except:
        flash(resp.text, "danger")
    finally:
        return redirect(url_for("samples.sample", sample_id=sample_id))


@samples_bp.route("/samples/<sample_id>/comment/<comment_id>", methods=["POST"])
@login_required
def hide_comment(sample_id, comment_id):
    """Hist comment for sample."""
    token = TokenObject(**current_user.get_id())
    # hide comment
    try:
        resp = remove_comment_from_sample(
            token, sample_id=sample_id, comment_id=comment_id
        )
    except Exception as error:
        flash(str(error), "danger")
    finally:
        return redirect(url_for("samples.sample", sample_id=sample_id))


@samples_bp.route("/samples/<sample_id>/qc_status", methods=["POST"])
@login_required
def update_qc_classification(sample_id):
    """Update the quality control report of a sample."""
    token = TokenObject(**current_user.get_id())

    # build data to store in db
    result = request.form.get("qc-validation", None)
    if result == "passed":
        action = None
        comment = ""
    elif result == "failed":
        comment = request.form.get("qc-comment", "")
        action = request.form.get("qc-action", "")
    else:
        raise ValueError(f"Unknown value of qc classification, {result}")

    try:
        update_sample_qc_classification(
            token, sample_id=sample_id, status=result, action=action, comment=comment
        )
    except Exception as error:
        flash(str(error), "danger")
    finally:
        return redirect(url_for("samples.sample", sample_id=sample_id))


@samples_bp.route("/samples/<sample_id>/resistance_report")
@login_required
def resistance_report(sample_id):
    """Samples view."""
    token = TokenObject(**current_user.get_id())
    sample = get_sample_by_id(token, sample_id=sample_id)
    return render_template(
        "resistance_report.html", title=f"{sample_id} resistance", sample=sample
    )


@samples_bp.route("/cluster/", methods=["GET", "POST"])
@login_required
def cluster(sample_id):
    """Samples view."""
    token = TokenObject(**current_user.get_id())

    if request.method == "POST":
        samples = request.body["samples"]
        cgmlst_cluster_samples(token, samples=samples)
    return render_template("sample.html", sample_id=sample_id)
