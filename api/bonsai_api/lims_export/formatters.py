"""Extract and format data for lims export."""

from collections import defaultdict
import logging
from typing import Any, Callable

from bonsai_api.models.qc import SampleQcClassification
from bonsai_api.models.sample import SampleInDatabase, ElementType, VariantInDb
from prp.models.phenotype import GeneBase, PredictionSoftware, VariantBase
from prp.models.typing import TypingMethod, TypingResultEmm


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


@register_formatter("mlst")
def mlst_typing(
    sample: SampleInDatabase, *, options: Any
) -> tuple[LimsAtomic, LimsComment]:
    """Extract and format MLST (Multi-Locus Sequence Typing) result from a sample."""
    options = options or {}
    for ty in sample.typing_result:
        if ty.type == "mlst":
            mlst_st = ty.result.sequence_type or "novel"
            return mlst_st, ""
    raise ValueError(f"Sample '{sample.sample_id}' doesn't have MLST results.")


@register_formatter("emm")
def emm_typing(
    sample: SampleInDatabase, *, options: Any
) -> tuple[LimsAtomic, LimsComment]:
    """Extract and format EMM result from a sample."""
    options = options or {}
    for ty in sample.typing_result:
        if ty.type == "emm":
            result: TypingResultEmm = ty.result
            return result.emmtype or "novel", ""
    raise ValueError(f"Sample '{sample.sample_id}' doesn't have EMM type.")


@register_formatter("species")
def species_prediction(
    sample: SampleInDatabase, *, options: Any
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
                    "Sample %s did not have any bracken predicitons", sample.sample_id
                )
                return None, ""
            # filter and sort
            rows = sorted(
                pred.result, key=lambda r: getattr(r, sort_by, 0.0), reverse=True
            )
            return rows[0].scientific_name, ""
    raise ValueError(
        f"Sample '{sample.sample_id}' dont have {preferred_software} species prediction result."
    )


@register_formatter("lineage")
def lineage_prediction(
    sample: SampleInDatabase, *, options: Any
) -> tuple[LimsAtomic, LimsComment]:
    """Get lineage information for a sample."""
    options = options or {}
    for pred in sample.typing_result:
        if (
            pred.type == TypingMethod.LINEAGE
            and pred.software == PredictionSoftware.TBPROFILER
        ):
            lin = pred.result.sublineage.replace("lineage", "")  # strip lineage
            return lin, ""
    raise ValueError(
        f"Sample '{sample.sample_id}' dont have tbprofiler prediction results."
    )


@register_formatter("qc")
def qc_status(
    sample: SampleInDatabase, *, options: Any
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
    sample: SampleInDatabase, *, options: Any
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
        if pred.software == preferred_software and pred.type == ElementType.AMR:
            variants = _resistance_variants(pred.result.variants, antibiotic_name, include_res_lvl)
            if variants is None:
                return None, ""
            return ", ".join(variants), ""
    raise ValueError(
        f"Sample '{sample.sample_id}' dont have AMR prediction from {preferred_software}."
    )


def _resistance_variants(variants: list[VariantInDb], antibiotic: str, resistance_lvl: str) -> list[str] | None:
    """Parse identified resistance variants."""
    passed_variants = [variant for variant in variants if variant.verified == "passed"]
    selected_variants: list[str] = []
    for variant in passed_variants:
        # skip variants that have not been currated or failed
        if not variant.verified == "passed":
            continue

        # skip variants that dont yeild resistance to antibiotic
        selected_phenotypes = [
            phe.name for phe in variant.phenotypes
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


def _serialize_variant(variant: VariantInDb) -> str:
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
