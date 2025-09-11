"""Export functions."""

import logging
from pathlib import Path
from typing import Any
from yaml import safe_load

from bonsai_api.models.sample import SampleInDatabase

from . import formatters
from .models import AssayConfig, ExportConfiguration, LimsRsResult


LOG = logging.getLogger(__name__)


def load_export_config(path: Path) -> ExportConfiguration:
    """Load a export configuration yaml file and return a config object."""
    LOG.debug("Loading config file: %s", path)
    if not path.is_file():
        raise FileNotFoundError(path)

    results: ExportConfiguration = []
    with path.open('r') as fh:
        yml: dict[str, Any] = safe_load(fh)
        for assay_name, content in yml.items():
            cnf = AssayConfig(assay=assay_name, fields=content.get('fields', []))
            results.append(cnf)
    return results


def lims_rs_formatter(sample: SampleInDatabase, config: AssayConfig):
    """Format sample information to LIMS-RS format using the provided configuration.
    
    The configuration specifies fields to inlcude, field name and formatting function.
    """
    LOG.debug("Preparing to format %s using assay %s", sample.sample_id, config.assay)
    result: list[LimsRsResult] = []
    for field in config.fields:
        match field.data_type:
            case "mlst":
                value, comment = formatters.get_mlst_typing(sample)
            case "species":
                value, comment = formatters.get_species_prediction(sample)
            case _:
                raise NotImplementedError(f"No formatter for data type: {field.data_type}")
        entry = LimsRsResult(
            sample_id=sample.sample_id,
            parameter_name=field.parameter_name,
            parameter_value=value,
            comment=comment,
        )
        result.append(entry)
    return result
