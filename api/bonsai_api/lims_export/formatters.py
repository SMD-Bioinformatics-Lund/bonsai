"""Extract and format data for lims export."""

import logging
from typing import Any, Callable

from bonsai_api.models.analysis import CurationRecord
from bonsai_api.models.qc import SampleQcClassification
from bonsai_api.models.sample import SampleRecordDb

from prp.parse.models.enums import AnalysisSoftware, AnalysisType
from prp.parse.models.typing import TypingResultEmm

from .models import Formatter, LimsAtomic, LimsComment, LimsValue

LOG = logging.getLogger(__name__)

_FORMATTERS: dict[str, Formatter] = {}


def register_formatter(name: str) -> Callable[[Formatter], Formatter]:
    """Decorator to register format functions by its data type."""

    def _decorator(fn: Formatter) -> Formatter:
        if name in _FORMATTERS:
            raise RuntimeError(f"Formatter '{name}' already registered.")
        _FORMATTERS[name] = fn
        return fn

    return _decorator


def get_formatter(name: str) -> Formatter:
    """Get format function with name."""
    try:
        return _FORMATTERS[name]
    except KeyError as err:
        raise NotImplementedError(
            f"No formatter registered for data type: {name}"
        ) from err


class AnalysisNotPresentError(Exception):
    """Raised if requested analysis is not in sample data."""


class AnalysisNoResultError(Exception):
    """Raised if requested analysis did not generate a result."""


@register_formatter("mlst")
def mlst_typing(
    sample: SampleRecordDb, *, options: Any
) -> tuple[LimsAtomic, LimsComment]:
    """Extract and format MLST (Multi-Locus Sequence Typing) result from a sample."""
    options = options or {}
    for av in sample.typing_result:
        if av.analysis_type == "mlst":
            mlst_st = av.result.sequence_type or "NA"
            if mlst_st is None:
                raise AnalysisNoResultError()
            return mlst_st, ""
    raise AnalysisNotPresentError(
        f"Sample '{sample.sample_name}' doesn't have MLST results."
    )


@register_formatter("emm")
def emm_typing(
    sample: SampleRecordDb, *, options: Any
) -> tuple[LimsAtomic, LimsComment]:
    """Extract and format EMM result from a sample."""
    options = options or {}
    for ty in sample.typing_result:
        if ty.type == "emmtype":
            result: TypingResultEmm = ty.result
            return result.emmtype or "NA", ""
    raise AnalysisNotPresentError(
        f"Sample '{sample.sample_name}' doesn't have EMM type."
    )


@register_formatter("species")
def species_prediction(
    sample: SampleRecordDb, *, options: Any
) -> tuple[LimsValue, LimsComment]:
    """Extract and format species prediction result using Bracken.

    Supported options:
        software: str                (default "bracken")
        sort_by: str                 (default for bracken "fraction_total_reads",
                                                  mykrobe "species_coverage")
    """
    options = options or {}
    preferred_software = options.get("software", "bracken")
    default_sort_by = (
        "fraction_total_reads"
        if preferred_software == "bracken"
        else "species_coverage"
    )
    sort_by = options.get("sort_by", default_sort_by)
    LOG.debug(
        "Get species prediction; software: %s, sort_by: %s", preferred_software, sort_by
    )

    for pred in sample.species_prediction:
        if pred.software == preferred_software:
            # ensure that best hit is first
            if len(pred.result) == 0:
                LOG.warning(
                    "Sample %s did not have any bracken predicitons", sample.sample_name
                )
                raise AnalysisNoResultError()
            # filter and sort
            rows = sorted(
                pred.result, key=lambda r: getattr(r, sort_by, 0.0), reverse=True
            )
            return rows[0].scientific_name, ""
    raise AnalysisNotPresentError(
        f"Sample '{sample.sample_name}' dont have {preferred_software} species prediction result."
    )


@register_formatter("lineage")
def lineage_prediction(
    sample: SampleRecordDb, *, options: Any
) -> tuple[LimsAtomic, LimsComment]:
    """Get lineage information for a sample."""
    options = options or {}
    for av in sample.typing_result:
        if (
            av.analysis_type == AnalysisType.LINEAGE
            and av.software == AnalysisSoftware.TBPROFILER
        ):
            if len(av.result) == 0:
                return "", ""

            sublineage = max(av.result, key=lambda x: len(x.lineage))
            return sublineage.lineage.replace("lineage", ""), ""
    raise AnalysisNotPresentError(
        f"Sample '{sample.sample_name}' dont have tbprofiler prediction results."
    )


@register_formatter("qc")
def qc_status(
    sample: SampleRecordDb, *, options: Any
) -> tuple[LimsAtomic, LimsComment]:
    """Get lineage information for a sample."""
    options = options or {}
    raw_status = sample.qc_status.status
    status = (
        raw_status.value
        if isinstance(raw_status, SampleQcClassification)
        else raw_status
    )
    return status.capitalize(), ""


@register_formatter("amr")
def amr_prediction_for_antibiotic(
    sample: SampleRecordDb, *, options: Any
) -> tuple[LimsAtomic, LimsComment]:
    """Get lineage information for a sample.

    Supported options:
        antibiotic_name: str
        software: str                (default "tbprofiler")
        resistance_level: str        (default "all")
    """
    options = options or {}
    preferred_software = options.get("software", "tbprofiler")
    antibiotic_name = options.get("antibiotic_name", "rifampicin")
    include_res_lvl = options.get("resistance_level", "all")

    accepted_variants: list[str] = []
    accepted_genes: list[str] = []  # TODO implement gene serialization

    for pred in sample.element_type_result:
        # Only consider AMR predictions from preferred software
        if pred.software != preferred_software and pred.analysis_type != AnalysisType.AMR:
            continue

        # Step 1: Collect relevant curations
        targeted_types = {"variant", "gene"}

        relevant_curations: list[CurationRecord] = [
            curr
            for curr in pred.curations
            if curr.decision == "accept"
            and curr.annotation_type in targeted_types
            and any(phe.name == antibiotic_name for phe in curr.phenotypes)
            and (
                include_res_lvl == "all" or any(
                    phe.name == antibiotic_name
                    and phe.meta.get("resistance_level") == include_res_lvl
                    for phe in curr.phenotypes
                )
            )
        ]

        # Skip this prediction if no curations apply
        if not relevant_curations:
            continue

        # Step 2: Index result entities for efficient lookup
        variants_by_id = {str(var.id): var for var in pred.result.variants}

        # Step 3: Resolve curations
        for curr in relevant_curations:
            if curr.annotation_type == "variant":
                var = variants_by_id.get(curr.result_key)
                if var is not None:
                    accepted_variants.append(_serialize_variant(var))
            elif curr.annotation_type == "gene":
                # TODO implement gene serialization
                pass
        
        # Step 4: return if anything was found
        if accepted_variants or accepted_genes:
            return ", ".join(accepted_variants + accepted_genes), ""
        
        # If curations existed but nothing was resolved, treat as no result
        raise AnalysisNoResultError()
    raise AnalysisNoResultError(
        f"Sample '{sample.sample_name}' dont have AMR prediction from {preferred_software}."
    )


def amr_prediction_for_antibiotic_back(
    sample: SampleRecordDb, *, options: Any
) -> tuple[LimsAtomic, LimsComment]:
    """Get lineage information for a sample.

    Supported options:
        antibiotic_name: str
        software: str                (default "tbprofiler")
        resistance_level: str        (default "all")
    """
    options = options or {}
    preferred_software = options.get("software", "tbprofiler")
    antibiotic_name = options.get("antibiotic_name", "rifampicin")
    include_res_lvl = options.get("resistance_level", "all")
    for pred in sample.element_type_result:
        if pred.software == preferred_software and pred.analysis_type == AnalysisType.AMR:
            # first filter for accepted variants and genes.
            targeted_types = ["variant", "gene"]
            accepted_markers = [
                curr 
                for curr 
                in pred.curations 
                if (curr.decision == "accept" and curr.annotation_type in targeted_types)]
            import pdb; pdb.set_trace()
            # then fetch curated variants from result
            # and format them to string representation
            accepted_variants = []
            for marker in accepted_markers:
                if marker.annotation_type == "variant" and antibiotic_name in marker.phenotypes:
                    variant = pred.result.variants[marker.target_index]
                    accepted_variants.append(_serialize_variant(variant))

            genes = []  # TODO implement formatting of genes
            if len(accepted_variants) == 0 and len(genes) == 0:
                raise AnalysisNoResultError()
            return ", ".join(accepted_variants + genes), ""
    raise AnalysisNotPresentError(
        f"Sample '{sample.sample_name}' dont have AMR prediction from {preferred_software}."
    )


def _resistance_variants(
    variants: list[Any], antibiotic: str, resistance_lvl: str
) -> list[str] | None:
    """Parse identified resistance variants."""
    passed_variants = [variant for variant in variants if variant.verified == "passed"]
    selected_variants: list[str] = []
    for variant in passed_variants:
        # skip variants that have not been currated or failed
        if not variant.verified == "passed":
            continue

        # skip variants that dont yeild resistance to antibiotic
        selected_phenotypes = [
            phe.name
            for phe in variant.phenotypes
            if (phe.resistance_level == resistance_lvl) or (resistance_lvl == "all")
        ]
        if antibiotic not in selected_phenotypes:
            continue

        selected_variants.append(_serialize_variant(variant))
        # serialize variant info to string representation
    # return none if no variants were found
    if len(selected_variants) == 0:
        return None
    return selected_variants


def _serialize_variant(variant: Any) -> str:
    """Serialize variant model to string representation."""
    who_classes = {
        "Assoc w R": 1,
        "Assoc w R - Interim": 2,
        "Uncertain significance": 3,
        "Not assoc w R - Interim": 4,
        "Not assoc w R": 5,
    }
    var_type = variant.variant_type
    if var_type == "SV":
        variant_desc = (
            f"g.{variant.start}_{variant.end}{variant.variant_subtype.lower()}"
        )
    else:
        variant_name = (
            variant.hgvs_nt_change
            if variant.hgvs_aa_change == ""
            else variant.hgvs_aa_change
        )
        variant_desc = f"{variant.reference_sequence}.{variant_name}"
    # annotate variant frequency for minority variants
    if variant.frequency is not None and variant.frequency < 1:
        variant_desc = f"{variant_desc}({variant.frequency * 100:.1f}%)"
    # annotate WHO classification
    who_group = who_classes.get(variant.phenotypes[0].note)
    if who_group is not None:
        variant_desc = f"{variant_desc} WHO-{who_group}"
    return variant_desc
