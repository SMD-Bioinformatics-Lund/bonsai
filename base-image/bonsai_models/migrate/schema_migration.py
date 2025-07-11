"""Functions to convert results to a new schema version."""

import logging
from copy import copy
from itertools import chain
from typing import Any, Callable

from bonsai_models.schema.pipeline.base import PipelineResult

from .v1_to_v2 import v1_to_v2

LOG = logging.getLogger(__name__)

UnformattedResult = dict[str, Any]


def migrate_result(
    old_result: UnformattedResult, validate: bool = True
) -> UnformattedResult | PipelineResult:
    """Migrate old JASEN result to the current schema.

    The final model can optionally be validated.
    """
    migration_funcs: dict[int, Callable[..., UnformattedResult]] = {2: v1_to_v2}

    # verify input
    input_schema_version = old_result["schema_version"]
    LOG.info("Migrating result from version %d", input_schema_version)
    valid_versions = (ver for ver in chain([1], migration_funcs.keys()))
    if input_schema_version not in valid_versions:
        all_versions = ", ".join([str(ver) for ver in migration_funcs])
        raise ValueError(
            f"Unknown result version, found {input_schema_version} expected any of '{all_versions}'"
        )

    # migrate
    temp_result = copy(old_result)
    for to_version, func in migration_funcs.items():
        if input_schema_version < to_version:
            temp_result = func(temp_result)

    # validate migrated model
    if validate:
        return PipelineResult.model_validate(temp_result)
    return temp_result
