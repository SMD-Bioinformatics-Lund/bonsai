"""Functions that generate data rendered by views."""

import logging
from collections import defaultdict
from itertools import chain, groupby
from typing import Any

import pandas as pd

from ...custom_filters import get_who_group_from_tbprofiler_comment
from ...models import ElementType, PredictionSoftware, QualityControlResult

LOG = logging.getLogger(__name__)
SampleObj = dict[str, Any]


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


def create_amr_summary(sample: SampleObj) -> tuple[dict[str, Any], dict[str, Any]]:
    """Summarize antimicrobial resistance prediction.

    :param sample: Sample information
    :type sample: SampleObj
    :raises ValueError: _description_
    :raises ValueError: _description_
    :return: Summary table and resistance information.
    :rtype: tuple[dict[str, Any], dict[str, Any]]
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


def sort_variants(sample_info: dict[str, Any]) -> dict[str, Any]:
    """Sort variants for a sample by verified status, ref sequence and position.

    :param sample_info: Sample object.
    :type sample_info: dict[str, Any]
    :return: Sample object with sorted variants.
    :rtype: dict[str, Any]
    """

    def _sort_func(variant: dict[str, Any]):
        """Sort on verfied status, by reference sequence name, and position."""
        sort_order = {"passed": 1, "unprocessed": 2, "failed": 3}
        return (
            sort_order[variant["verified"]],
            variant["reference_sequence"],
            variant["start"],
        )

    # sort the filtered variants by verification status and then gene name
    for pred_res in sample_info["element_type_result"]:
        sorted_variants = sorted(pred_res["result"]["variants"], key=_sort_func)
        pred_res["result"]["variants"] = sorted_variants

    # sort SNV and SV variants
    for variant_type in ["snv_variants", "sv_variants"]:
        if sample_info.get(variant_type) is not None:
            sample_info[variant_type] = sorted(
                sample_info[variant_type], key=_sort_func
            )

    return sample_info


def has_variant_passed_filters(variant: dict[str, Any], form: dict[str, Any]) -> bool:
    """Check if variant passes qc filters."""
    variant_passes_qc = True
    # check frequency
    min_freq = form.get("min-frequency")
    if min_freq and variant.get("frequency") is not None:
        LOG.error("%s == %s", min_freq, variant["frequency"] * 100)
        if form.get("freq-operator") == "gte":
            variant_passes_qc = variant["frequency"] * 100 >= int(min_freq)
        else:
            variant_passes_qc = variant["frequency"] * 100 <= int(min_freq)

    # check read depth
    min_depth = form.get("min-depth")
    if min_depth and variant["depth"] is not None:
        if form.get("depth-operator") == "gte":
            variant_passes_qc = variant["depth"] >= int(min_depth)
        else:
            variant_passes_qc = variant["depth"] <= int(min_depth)

    # hide variant that have been manually dismissed
    if bool(form.get("hide-dismissed")) and variant["verified"] == "failed":
        variant_passes_qc = False

    # hide varians without resistance
    if bool(form.get("yeild-resistance")) and len(variant.get("phenotypes", [])) == 0:
        variant_passes_qc = False

    # only inlcude variants of selected types
    selected_var_types = form.getlist("filter-variant-type")
    if selected_var_types and variant["variant_type"] not in selected_var_types:
        variant_passes_qc = False

    # only inlcude variants in selected genes
    selected_genes = form.getlist("filter-genes")
    if selected_genes and variant["reference_sequence"] not in selected_genes:
        variant_passes_qc = False

    # only inlcude variants with desired WHO class
    selected_who_classes = form.getlist("filter-who-class")
    # get who classes for a variant
    n_intersecting_classes = len(
        set(selected_who_classes) & set(get_variant_classifications(variant))
    )
    if selected_who_classes and n_intersecting_classes == 0:
        variant_passes_qc = False

    return variant_passes_qc


def filter_variants(
    sample_info: dict[str, Any], form: dict[str, Any] = {}
) -> dict[str, Any]:
    """Filter resistance variants from prediction sw."""
    for prediction in sample_info["element_type_result"]:
        variants = prediction["result"]["variants"]
        if len(variants) == 0:
            continue
        # build up a new variant list that passes all filtering criteria
        filtered_variants = [
            variant for variant in variants if has_variant_passed_filters(variant, form)
        ]
        # replace variants with filtered variants
        prediction["result"]["variants"] = filtered_variants

    # filter SNV and SV variants
    for variant_type in ["snv_variants", "sv_variants"]:
        variants = sample_info.get(variant_type)
        if variants is not None:
            filtered_variants = [
                variant
                for variant in variants
                if has_variant_passed_filters(variant, form)
            ]
            sample_info[variant_type] = filtered_variants
    return sample_info


def get_variant_genes(sample_info, software=None) -> tuple[str, ...]:
    """Get the genes that have variants."""
    genes = set()
    for prediction in sample_info["element_type_result"]:
        # skip predictions that are not resistance
        if not prediction["type"] == "AMR":
            continue
        # skip predictions that are not madew with the desired software
        if software and not software == prediction["software"]:
            continue
        # skip predictions withouht variants
        variants = prediction["result"]["variants"]
        genes.update({variant["reference_sequence"] for variant in variants})
    return tuple(sorted(genes))


def get_variant_classifications(variant) -> tuple[str, ...]:
    """Get the the classifications for a single variant."""
    classification = set()
    for pheno in variant["phenotypes"]:
        who_group = get_who_group_from_tbprofiler_comment(pheno)
        if who_group:
            classification.update([who_group])
    return tuple(list(classification))


def get_all_who_classifications(sample_info, software=None) -> tuple[str, ...]:
    """Get the classification of variants predicted by a given software."""
    classification = set()
    for prediction in sample_info["element_type_result"]:
        # skip predictions that are not resistance
        if not prediction["type"] == "AMR":
            continue
        # skip predictions that are not made w with the desired software
        if software and not prediction["software"] == software:
            continue
        # skip predictions withouht variants
        variants = prediction["result"]["variants"]
        for variant in variants:
            classification.update(get_variant_classifications(variant))
    return tuple(sorted(classification))


def get_all_variant_types(sample_info, software=None) -> tuple[str, ...]:
    """Get all variant types in the sample output."""
    variant_types = set()
    for prediction in sample_info["element_type_result"]:
        # skip predictions that are not resistance
        if not prediction["type"] == "AMR":
            continue
        # skip predictions that are not made w with the desired software
        if software and not prediction["software"] == software:
            continue
        # skip predictions withouht variants
        variants = {
            variant["variant_type"] for variant in prediction["result"]["variants"]
        }
        variant_types.update(variants)
    return tuple(sorted(variant_types))


def filter_variants_if_processed(sample_info, result_type="AMR"):
    """Filter out unprocessed and failed variants if any variants have been processed."""
    results = []
    for result in sample_info["element_type_result"]:
        if result["type"] == "AMR" and len(result["result"]["variants"]) > 0:
            # check if result has has processed variants
            processed = [QualityControlResult.FAILED, QualityControlResult.PASSED]
            has_proc_variants = any(
                QualityControlResult(var["verified"]) in processed
                for var in result["result"]["variants"]
            )
            # create filtered variant object
            if has_proc_variants:
                # remove failed and unprocessed variants
                variants = [
                    var
                    for var in result["result"]["variants"]
                    if QualityControlResult(var["verified"])
                    == QualityControlResult.PASSED
                ]
            else:
                # include all
                variants = result["result"]["variants"]
            # update variant object
            result["result"]["variants"] = variants
        # add back the result object to the sample info data
        results.append(result)
    # add back the result object to the sample info data
    sample_info["element_type_result"] = results
    return sample_info


def split_metadata(sample_obj: dict[str, Any]):
    """Seperate key-value metadata records from tables into two distinct collections."""
    kw_meta: list[dict[str, Any]] = []
    tbl_meta: list[dict[str, Any]] = []
    for meta in sample_obj["metadata"]:
        if meta["type"] == "table":
            tbl_meta.append(meta)
        else:
            kw_meta.append(meta)
    return kw_meta, tbl_meta


def kw_metadata_to_table(metadata: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Format key-value metadata to a dataframe like table object."""
    grouped_kw_meta: dict[str, dict[str, Any]] = {}
    for name, records_itr in groupby(metadata, key=lambda x: x["category"]):
        records = list(records_itr)
        raw_series = pd.Series(
            [rec["value"] for rec in records],
            index=[rec["fieldname"] for rec in records],
            name="Metadata",
        )
        grouped_kw_meta[name] = raw_series.to_frame().to_dict("split")
    return grouped_kw_meta
