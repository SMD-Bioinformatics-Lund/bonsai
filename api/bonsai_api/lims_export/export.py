"""Export functions."""

import logging
from pathlib import Path
from typing import Any

from bonsai_api.models.sample import SampleInDatabase
from yaml import safe_load

from .formatters import get_formatter
from .models import AssayConfig, ExportConfiguration, LimsRsResult, LimsValue

LOG = logging.getLogger(__name__)


def load_export_config(path: Path) -> ExportConfiguration:
    """Load a export configuration yaml file and return a config object."""
    LOG.debug("Loading config file: %s", path)
    if not path.is_file():
        raise FileNotFoundError(path)

    results: ExportConfiguration = []
    with path.open("r") as fh:
        yml: dict[str, Any] = safe_load(fh)
        for assay_name, content in yml.items():
            cnf = AssayConfig(assay=assay_name, fields=content.get("fields", []))
            results.append(cnf)
    return results


def _to_str(value: LimsValue) -> str:
    if value is None:
        return ""
    # optional serialization rules
    return str(value)


def lims_rs_formatter(sample: SampleInDatabase, config: AssayConfig):
    """Format sample information to LIMS-RS format using the provided configuration.

    The configuration specifies fields to inlcude, field name and formatting function.
    """
    LOG.debug("Preparing to format %s using assay %s", sample.sample_id, config.assay)
    result: list[LimsRsResult] = []
    for field in config.fields:
        formatter = get_formatter(field.data_type)

        try:
            value, comment = formatter(sample, options=field.options)
            missing = (value is None) or (value == "")
            if missing and field.required:
                raise ValueError(
                    f"Required field '{field.parameter_name}' ({field.data_type}) is missing."
                )
            entry = LimsRsResult(
                sample_id=sample.sample_id,
                parameter_name=field.parameter_name,
                parameter_value=_to_str(value),
                comment=comment or "",
            )
            result.append(entry)
        except Exception as err:
            LOG.error("An unexpected error occured, %s", err)
            raise
    return result
