"""Extract and format data for lims export."""

import logging
from typing import Any, Callable

from bonsai_api.models.qc import SampleQcClassification
from bonsai_api.models.sample import SampleInDatabase
from prp.models.phenotype import PredictionSoftware
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
        software: str                (default "tbprofiler")
    """
    options = options or {}
    preferred_software = options.get("software", "tbprofiler")
    for pred in sample.element_type_result:
        if pred.software == preferred_software:
            return "", ""
    raise ValueError(
        f"Sample '{sample.sample_id}' dont have AMR prediction from {preferred_software}."
    )
