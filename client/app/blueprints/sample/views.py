"""Declaration of views for samples"""
from flask import (
    Blueprint,
    current_app,
    render_template,
    redirect,
    url_for,
    request,
    flash,
)
from app.mimer import (
    cgmlst_cluster_samples,
    get_sample_by_id,
    get_group_by_id,
    post_comment_to_sample,
    remove_comment_from_sample,
    TokenObject,
)
from flask_login import login_required, current_user
from itertools import chain

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
    return render_template(
        "sample.html", sample=sample, title=sample_id, is_filtered=bool(group_id)
    )


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
    except:
        flash(resp.text, "danger")
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
