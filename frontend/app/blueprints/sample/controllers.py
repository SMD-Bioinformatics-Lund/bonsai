"""Functions that generate data rendered by views."""
import logging
from collections import defaultdict
from itertools import chain, groupby
from typing import Any, Dict, Tuple

from app.models import NT_TO_AA, ElementType, PredictionSoftware

LOG = logging.getLogger(__name__)
SampleObj = Dict[str, Any]


def _has_phenotype(feature, phenotypes) -> bool:
    """Check if gene or mutation has phenotype."""
    phenotypes = [phe.lower() for phe in phenotypes]
    return any(pheno.lower() in phenotypes for pheno in feature["phenotypes"])


def filter_validated_genes(validated_genes, sample: SampleObj):
    """Remove genes that have not been validated.

    :param validated_genes: Genes that have been validated
    :type validated_genes: _type_
    :param sample: Sample prediction result
    :type sample: SampleObj
    :return: Validated genes
    """
    for category, valid_genes in validated_genes.items():
        LOG.debug("Removing non-validated genes from input")
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
    return pred_res


def to_hgvs_nomenclature(variant):
    """Format variant to HGVS variant nomenclature."""
    ref_gene = ""
    if variant["ref_id"] is not None:
        _, _, raw_accnr = variant["ref_id"].split(";;")
        accnr = raw_accnr.split("_")[0]
        ref_gene = f"{accnr}:g."
    pos = variant["position"]
    ref_nt = variant["ref_nt"]
    alt_nt = variant["alt_nt"]
    match variant["variant_type"]:
        case "substitution":
            description = f"{pos}{ref_nt}>{alt_nt}"
        case "deletion":
            description = f"{pos}_{pos + len(ref_nt)}del"
        case "insertion":
            description = f"{pos}_{pos + len(alt_nt)}int{alt_nt.upper()}"
    return f"{ref_gene}{description}"


def create_amr_summary(sample: SampleObj) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Summarize antimicrobial resistance prediction.

    :param sample: Sample information
    :type sample: SampleObj
    :raises ValueError: _description_
    :raises ValueError: _description_
    :return: Summary table and resistance information.
    :rtype: Tuple[Dict[str, Any], Dict[str, Any]]
    """
    amr_summary = {}
    resistance_info = {"genes": {}, "mutations": defaultdict(list)}
    LOG.debug("Make AMR prediction summary table")
    for pred_res in sample["element_type_result"]:
        # only get AMR resistance
        if pred_res["type"] == ElementType.AMR.value:
            for gene in pred_res["result"]["genes"]:
                gene_name = gene["gene_symbol"]
                if gene_name is None:
                    raise ValueError
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
                if mutation["ref_id"] is None:
                    continue
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
                    ref_aa = mutation["ref_aa"].upper()
                    alt_aa = mutation["alt_aa"].upper()
                    gene_entry["change"] = f"{ref_aa}{mutation['position']}{alt_aa}"
                else:
                    raise ValueError
                # store object
                amr_summary[gene_name] = gene_entry
                mutation["name"] = to_hgvs_nomenclature(mutation)
                resistance_info["mutations"][gene_name].append(mutation)

    # group summary by res_class
    amr_summary = {
        res_type: list(rows)
        for res_type, rows in groupby(
            amr_summary.values(), key=lambda x: x["res_class"]
        )
    }
    return amr_summary, resistance_info


def sort_variants(sample_info: Dict[str, Any]) -> Dict[str, Any]:
    """Sort variants for a sample by verified status, ref sequence and position.

    :param sample_info: Sample object.
    :type sample_info: Dict[str, Any]
    :return: Sample object with sorted variants.
    :rtype: Dict[str, Any]
    """
    def _sort_func(variant):
        """Sort on verfied status, by reference sequence name, and position."""
        SORT_ORDER = {"passed": 1, "unprocessed": 2, "failed": 3}
        return (SORT_ORDER[variant["verified"]], variant["reference_sequence"], variant["start"])

    # sort the filtered variants by verification status and then gene name
    for pred_res in sample_info["element_type_result"]:
        sorted_variants = sorted(
            pred_res["result"]["variants"],
            key=_sort_func
        )
        pred_res["result"]["variants"] = sorted_variants

    # sort SNV and SV variants
    for variant_type in ["snv_variants", "sv_variants"]:
        sample_info[variant_type] = sorted(sample_info[variant_type], key=_sort_func)

    return sample_info


def has_variant_passed_filters(variant: Dict[str, Any], form: Dict[str, Any]) -> bool:
    """Check if variant passes qc filters."""
    variant_passes_qc = True
    # check frequency
    min_freq = form.get("min-frequency")
    if min_freq and (variant["frequency"] * 100) < int(min_freq):
        LOG.error("%s == %s", min_freq, variant["frequency"] * 100)
        variant_passes_qc = False

    # check read depth
    min_depth = form.get("min-depth")
    if min_depth and variant["depth"] < int(min_depth):
        variant_passes_qc = False

    # hide variant that have been manually dismissed
    if bool(form.get("hide-dismissed")) and variant["verified"] == "failed":
        variant_passes_qc = False

    # hide varians without resistance
    if (
        bool(form.get("yeild-resistance"))
        and len(variant.get("phenotypes", [])) == 0
    ):
        variant_passes_qc = False

    # only inlcude variants in selected genes
    selected_genes = form.getlist("filter-genes")
    if selected_genes and variant["reference_sequence"] not in selected_genes:
        variant_passes_qc = False

    return variant_passes_qc


def filter_variants(sample_info, form: float | None = None):
    # filter resistance variants from prediction sw
    for prediction in sample_info["element_type_result"]:
        variants = prediction["result"]["variants"]
        if len(variants) == 0:
            continue
        # build up a new variant list that passes all filtering criteria
        filtered_variants = [
            variant for variant in variants 
            if has_variant_passed_filters(variant, form)
        ]
        # replace variants with filtered variants
        prediction["result"]["variants"] = filtered_variants

    # filter SNV and SV variants
    for variant_type in ["snv_variants", "sv_variants"]:
        variants = sample_info.get(variant_type)
        if variants is not  None:
            filtered_variants = [
                variant for variant in variants 
                if has_variant_passed_filters(variant, form)
            ]
            sample_info[variant_type] = filtered_variants
    return sample_info


def get_variant_genes(sample_info, software=None) -> Tuple[str, ...]:
    genes = set()
    for prediction in sample_info["element_type_result"]:
        # skip predictions that are not madew with the desired software
        if software and software == prediction["type"]:
            continue
        # skip predictions withouht variants
        variants = prediction["result"]["variants"]
        genes.update({variant["reference_sequence"] for variant in variants})
    return tuple(sorted(genes))
