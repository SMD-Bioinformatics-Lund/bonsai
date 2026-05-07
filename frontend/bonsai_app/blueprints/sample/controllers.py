"""Functions that generate data rendered by views."""

from dataclasses import dataclass
import logging
from collections import defaultdict
from itertools import chain, groupby
from typing import Any

import pandas as pd
from requests import HTTPError

from bonsai_app.bonsai import TokenObject, create_curation, VariantCurationRecord, PhenotypeAnnotation

from bonsai_app.custom_filters import get_who_group_from_tbprofiler_comment
from bonsai_app.models import ElementType, PredictionSoftware, QualityControlResult

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


def get_results_by(sample_info: SampleObj, *, software: str | None = None, analysis_type: str | None = None) -> list[dict[str, Any]]:
    """Get prediction results for a given software and/or analysis type.

    :param sample_info: Sample object containing element_type_result
    :type sample_info: SampleObj
    :param software: Optional software filter (case-insensitive)
    :type software: str | None
    :param analysis_type: Optional analysis type filter (case-insensitive)
    :type analysis_type: str | None
    :return: List of matching prediction results
    :rtype: list[dict[str, Any]]
    """
    results = []
    for res in sample_info.get("element_type_result", []):
        if software and res.get("software", "").lower() != software.lower():
            continue
        if analysis_type and res.get("analysis_type", "").lower() != analysis_type.lower():
            continue
        results.append(res)
    return results


def sort_variants(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort a list of variants by verified status, reference sequence, and position.

    Sorts in order: verified status (passed → unprocessed → failed), 
    then by reference sequence name, then by position.

    :param variants: List of variant dictionaries to sort
    :type variants: list[dict[str, Any]]
    :return: Sorted list of variants
    :rtype: list[dict[str, Any]]
    """
    def _sort_key(variant: dict[str, Any]) -> tuple:
        """Generate sort key based on verification status, ref sequence, and position."""
        sort_order = {"passed": 1, "unprocessed": 2, "failed": 3}
        return (
            sort_order.get(variant.get("verified", "unprocessed"), 999),
            variant.get("reference_sequence", ""),
            variant.get("start", 0),
        )

    return sorted(variants, key=_sort_key)


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
        if not prediction["analysis_type"] == "amr":
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
        if not prediction["analysis_type"] == "amr":
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
        if not prediction["analysis_type"] == "amr":
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
        if result["analysis_type"] == "amr" and len(result["result"]["variants"]) > 0:
            # check if result has has processed variants
            processed = [QualityControlResult.FAILED, QualityControlResult.PASSED]
            has_proc_variants = any(
                QualityControlResult(var.get("verifeid", "unprocessed")) in processed
                for var in result["result"]["variants"]
            )
            # create filtered variant object
            if has_proc_variants:
                # remove failed and unprocessed variants
                variants = [
                    var
                    for var in result["result"]["variants"]
                    if QualityControlResult(var.get("verified", "unprocessed"))
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


@dataclass
class CurationResult:
    """Result of a single curation submission."""
    variant_id: str
    analysis_id: str
    success: bool
    response: dict | None = None
    error: str | None = None


def build_curation_records(
    records: list[dict[str, str]],
    decision: str,
    rejection_reason: dict | None = None,
    phenotypes: list[str] | None = None,
    resistance_level: str | None = None,
) -> list[dict[str, str | VariantCurationRecord]]:
    """Build curation record payloads.
    
    Validates and structures curation data for API submission.
    """
    if not records:
        raise ValueError("At least one curation record required")
    
    if decision == "rejected" and not rejection_reason:
        raise ValueError("Rejection reason required when rejecting variants")
    
    meta = {"resistance_level": resistance_level} if resistance_level else {}
    phenotype_records = [PhenotypeAnnotation(name=p, meta=meta) for p in phenotypes] if phenotypes else []
    
    return [
        {
            "analysis_id": rec["analysis_id"],
            "analysis_type": rec["analysis_type"],
            "curation": VariantCurationRecord(
                result_key=rec["variant_id"],
                annotation_type="variant",
                decision=decision,
                rejection_reason=rejection_reason["description"] if rejection_reason else None,
                phenotypes=phenotype_records,
            )
            } for rec in records
    ]


def submit_curations_batch(
    token: TokenObject,
    records: list[dict[str, str | VariantCurationRecord]],
) -> list[CurationResult]:
    """Submit multiple curation records and aggregate results.
    
    Handles errors gracefully and returns detailed results.
    Returns all results (successes and failures) for reporting.
    """
    results = []
    
    for rec in records:
        analysis_id = rec["analysis_id"]
        analysis_type = rec["analysis_type"]
        curation_record = rec["curation"]
        try:
            resp = create_curation(token, analysis_type=analysis_type, analysis_id=analysis_id, record=curation_record)
            results.append(CurationResult(
                variant_id=curation_record.result_key,
                analysis_id=analysis_id,
                success=True,
                response=resp,
            ))
            LOG.info("Curation created for variant %s in analysis %s", 
                    curation_record.result_key, analysis_id)
        except HTTPError as err:
            LOG.warning(
                "HTTP error creating curation for %s: %s",
                curation_record.result_key, err.response.status_code
            )
            results.append(CurationResult(
                variant_id=curation_record.result_key,
                analysis_id=analysis_id,
                success=False,
                error=f"HTTP {err.response.status_code}: {err.response.text}",
            ))
        except Exception as err:
            LOG.error("Unexpected error creating curation for %s: %s", 
                     curation_record.result_key, str(err))
            results.append(CurationResult(
                variant_id=curation_record.result_key,
                analysis_id=analysis_id,
                success=False,
                error=str(err),
            ))
    
    return results


def merge_variants_with_curations(analysis_result: dict[str, Any]) -> dict[str, Any]:
    """Merge variant curation data into the analysis result for frontend display.

    Takes an analysis result (e.g., from element_type_result) and enriches each variant
    with its curation status, decision, and phenotypes from the embedded curations.

    :param analysis_result: Single analysis result dict with 'result' and 'curations' keys
    :return: Modified analysis_result with variants enriched with curation data
    """
    if "result" not in analysis_result or "variants" not in analysis_result["result"]:
        return analysis_result  # No variants to process

    if "curations" not in analysis_result:
        return analysis_result  # No curations to merge

    # Build lookup of curations by result_key (variant ID)
    curation_lookup = {
        curation["result_key"]: curation
        for curation in analysis_result["curations"]
        if curation.get("annotation_type") == "variant"
    }

    # Enrich each variant with curation data
    for variant in analysis_result["result"]["variants"]:
        variant_id = str(variant.get("id") or variant.get("variant_id"))
        if variant_id in curation_lookup:
            curation = curation_lookup[variant_id]
            variant["curation"] = {
                "decision": curation.get("decision"),
                "rejection_reason": curation.get("rejection_reason"),
                "notes": curation.get("notes"),
                "phenotypes": curation.get("phenotypes", []),
                "curated_by": curation.get("curated_by"),
                "curated_at": curation.get("created_at"),
                "approved_by": curation.get("approved_by"),
            }
        else:
            variant["curation"] = None  # No curation for this variant

    return analysis_result