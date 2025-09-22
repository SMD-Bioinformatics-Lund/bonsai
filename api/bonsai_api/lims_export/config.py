"""Functions for loading configuration."""


import logging
from importlib import resources
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from yaml import YAMLError, safe_load

from .models import AssayConfig, ExportConfiguration

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


def get_lims_config_for_assay(assay: str) -> AssayConfig | None:
    """Get LIMS export configuration for pipeline assay"""
    conf_obj = load_export_config(settings.lims_export_config)
    for cnf in conf_obj:
        if cnf.assay == assay:
            return cnf
    return None
