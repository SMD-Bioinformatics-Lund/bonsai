"""Declaration of views for samples"""
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash,
)
from app.bonsai import (
    cgmlst_cluster_samples,
    cluster_samples,
    get_sample_by_id,
    get_group_by_id,
    post_comment_to_sample,
    remove_comment_from_sample,
    find_samples_similar_to_reference,
    TokenObject,
)
from flask_login import login_required, current_user
from itertools import chain, groupby
from app.models import ElementType, PredictionSoftware, NT_TO_AA

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

    # summarize predicted antimicrobial resistance
    amr_summary = {}
    resistance_info = {"genes": {}, "mutations": {}}
    for pred_res in sample["element_type_result"]:
        # only get AMR resistance
        if pred_res["type"] == ElementType.AMR.value:
            for gene in pred_res["result"]["genes"]:
                gene_name = gene["gene_symbol"]
                if gene_name is None:
                    raise ValueError()
                # get/create summary dictionary object
                gene_entry = amr_summary.get(
                    gene_name, {
                        # create default object
                        "gene_symbol": gene_name,
                        "software": [],
                        "res_class": "Unknown"
                    })
                # annotate softwares
                gene_entry['software'].append(pred_res["software"])

                # annotate resistance class
                if pred_res["software"] == PredictionSoftware.AMRFINDER.value:
                    gene_entry['res_class'] = gene["res_class"]

                # store object
                amr_summary[gene_name] = gene_entry

                # reformat resistance gene table
                gene_entry = resistance_info['genes'].get(gene_name, [])
                gene['software'] = pred_res['software']
                gene_entry.append(gene)
                resistance_info['genes'][gene_name] = gene_entry

            # iterate over mutations and populate resistance summaries
            for mutation in pred_res["result"]["mutations"]:
                gene_name, *_ = mutation["ref_id"].split(';;')
                # gene entries
                gene_entry = amr_summary.get(
                    gene_name, {
                        # create default object
                        "gene_symbol": gene_name,
                        "software": [],
                        "res_class": "Unknown"
                    })
                if mutation['variant_type'] == 'substitution':
                    ref_aa = NT_TO_AA[mutation['ref_codon'].upper()]
                    alt_aa = NT_TO_AA[mutation['alt_codon'].upper()]
                    gene_entry['change'] = f"{ref_aa}{mutation['position']}{alt_aa}"
                else:
                    raise ValueError()
                # store object
                amr_summary[gene_name] = gene_entry

    # group summary by res_class
    amr_summary = {
        res_type: list(rows) 
        for res_type, rows 
        in  groupby(amr_summary.values(), key=lambda x: x['res_class'])
    }

    # Get the 10 most similar samples and calculate the pair-wise similaity
    similar_samples = find_samples_similar_to_reference(
        token, sample_id=sample_id, limit=10
    )
    # cluster the similar samples
    TYPING_METHOD = "minhash"
    LINKAGE = "single"
    newick_file = cluster_samples(
        token, 
        sample_ids=[smp["sample_id"] for smp in similar_samples["samples"]],
        typing_method=TYPING_METHOD, method=LINKAGE)
    similar_samples = {"typing_method": TYPING_METHOD, "method": LINKAGE, "newick": newick_file}

    return render_template(
        "sample.html", sample=sample, amr_summary=amr_summary, resistance_info=resistance_info,
        title=sample_id, is_filtered=bool(group_id), similar_samples=similar_samples
    )


@samples_bp.route("/samples/<sample_id>/similar", methods=["POST"])
@login_required
def find_similar_samples(sample_id):
    """Find samples that are similar."""
    token = TokenObject(**current_user.get_id())
    similarity = request.json.get('similarity', 0.5)
    try:
        resp = find_samples_similar_to_reference(
            token, sample_id=sample_id, similarity=similarity
        )
    except Exception as error:
        return {"status": 500, "details": str(error)}, 500
    return resp, 200


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
