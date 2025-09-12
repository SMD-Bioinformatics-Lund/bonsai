"""Export functions."""

import csv
import io
import logging
from pathlib import Path
from typing import Any, Literal
from importlib import resources

from pydantic import ValidationError

from bonsai_api.models.sample import SampleInDatabase
from yaml import YAMLError, safe_load

from .formatters import AnalysisNoResultError, AnalysisNotPresentError, get_formatter
from .models import AssayConfig, ExportConfiguration, LimsRsResult, LimsValue

LOG = logging.getLogger(__name__)


class InvalidFormatError(Exception):
    """Raised if there is a likely issue with the file format."""


def load_export_config(path: Path | None) -> ExportConfiguration:
    """Load a export configuration yaml file and return a config object.
    
    If `path` is not provided, loads the default configuration packaged with Bonsai
    at `bonsai_api.resources/default_lims_export.yml`.

    Returns:
        list[AssayConfig]: Validated configuration entries.

    Raises:
        FileNotFoundError: If the provided path does not point to a file.
        InvalidFormatError: If YAML parsing fails or the content does not match the expected schema.
    """
    # 1. open input stream, either from file system or packaged resources
    if path is None:
        # open default LIMS export configuration file
        resource = resources.files("bonsai_api.resources") / "default_lims_export.yml"
        source_for_msgs = str(resource)
        LOG.debug("Loading default packaged config: %s", source_for_msgs)
        stream_ctx = resource.open('r', encoding="utf-8")
    else:
        source_for_msgs = str(path)
        LOG.debug("Loading config file: %s", path)
        if not path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        if path.suffix.lower() not in {".yaml", ".yml"}:
            LOG.warning("Configuration file does not have a .yaml/.yml extension: %s", path)
        stream_ctx = path.open('r', encoding="utf-8")

    # 2. Parse YAML and convert to data model
    with stream_ctx as fh:
        try:
            data: Any = safe_load(fh)
        except YAMLError as err:
            # Include the specific YAML error class and a short hint
            raise InvalidFormatError(
                f"Failed to parse YAML from {source_for_msgs}: {err.__class__.__name__}: {err}"
            ) from err
    # Empty file yeilds None
    if data is None:
        raise InvalidFormatError(
            f"Invalid configuration in {source_for_msgs}: empty file. "
            "Expected a YAML list of assay configuration entries"
        )
    
    # 3. Validate shape of data
    if not isinstance(data, list):
        raise InvalidFormatError(
            f"Invalid configuration in {source_for_msgs}: expected a YAML sequence (list) of entries, "
            f"got {type(data).__name__}. Example:\n"
            "- name: example\n"
            "  field_a: value\n"
            "  field_b: value"
        )

    results: ExportConfiguration = []
    errors: list[str] = []

    # 4. Validate configuration
    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            errors.append(f"item {idx}: expected a mapping (dict), got {type(entry).__name__}")
            continue
        try:
            cnf = AssayConfig.model_validate(entry)
            results.append(cnf)
        except ValidationError as err:
            errors.append(f"item: {idx}: {err}")
    
    if errors:
        joined = "\n".join(f"- {err}" for err in errors)
        raise InvalidFormatError(
            f"Configuration validation failed for {source_for_msgs}:\n{joined}\n"
            "Fix the above item(s) to proceed."

        )
    return results


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
    LOG.debug("Preparing to format %s using assay %s", sample.sample_id, config.assay)
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
                sample.sample_id,
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
                f"({field.data_type}) is not present on sample '{sample.sample_id}'."
            )
        entry = LimsRsResult(
            sample_id=sample.sample_id,
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
                result.sample_id,
                result.parameter_name,
                result.parameter_value,
                result.comment,
            ]
        )

    return output.getvalue()
