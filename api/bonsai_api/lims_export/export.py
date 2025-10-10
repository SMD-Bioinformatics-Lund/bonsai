"""Export functions."""

import csv
import io
import logging
from typing import Literal

from bonsai_api.models.sample import SampleInDatabase

from .formatters import AnalysisNoResultError, AnalysisNotPresentError, get_formatter
from .models import AssayConfig, LimsRsResult, LimsValue

LOG = logging.getLogger(__name__)


def _to_str(value: LimsValue) -> str:
    if value is None or value == "":
        return "-"
    # optional serialization rules
    return str(value)


def lims_rs_formatter(
    sample: SampleInDatabase, config: AssayConfig
) -> list[LimsRsResult]:
    """Format sample information to LIMS-RS format using the provided configuration.

    Semantics:
      - required=True ⇒ the *analysis* must be attached to the sample
      - analysis present but no result ⇒ include a row with value=None (empty after _to_str)
      - analysis not present and required ⇒ raise ValueError
    """
    LOG.debug("Preparing to format %s using assay %s", sample.sample_name, config.assay)
    result: list[LimsRsResult] = []
    for field in config.fields:
        formatter = get_formatter(field.data_type)
        analysis_present = True  # assume present unless formatter says otherwise

        try:
            value, comment = formatter(sample, options=field.options)
        except AnalysisNotPresentError as e:
            # Analysis has not been done on this sample
            analysis_present = False
            value, comment = None, "not_present"

        except AnalysisNoResultError as e:
            # Analysis is present but no failed to generate a result
            value, comment = None, "no_result"

        except Exception as err:
            LOG.error(
                "Unexpected error formatting sample=%s field=%s (%s): %s",
                sample.sample_name,
                field.parameter_name,
                field.data_type,
                err,
                exc_info=True,
            )
            raise

        # Enforce presence requirement only on 'not present'
        if field.required and not analysis_present:
            raise ValueError(
                f"Required analysis for field '{field.parameter_name}' "
                f"({field.data_type}) is not present on sample '{sample.sample_name}'."
            )
        entry = LimsRsResult(
            sample_name=sample.sample_name,
            parameter_name=field.parameter_name,
            parameter_value=_to_str(value),  # None -> "", int/str -> str
            comment=comment or "",
        )
        result.append(entry)
    return result


def serialize_lims_results(
    results: list[LimsRsResult], delimiter: Literal["csv", "tsv"] = "csv"
) -> str:
    """Serialize lims result to tabular format."""
    output = io.StringIO()
    writer = csv.writer(
        output, delimiter="," if delimiter == "csv" else "\t", quoting=csv.QUOTE_MINIMAL
    )

    # Write header
    writer.writerow(["sample_id", "parameter_name", "parameter_value", "comment"])

    # Write rows
    for result in results:
        writer.writerow(
            [
                result.sample_name,
                result.parameter_name,
                result.parameter_value,
                result.comment,
            ]
        )

    return output.getvalue()
