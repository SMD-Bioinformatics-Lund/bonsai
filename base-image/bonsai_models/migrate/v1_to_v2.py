"""Migrate from input version 1 to 2."""

import logging
from copy import copy
from typing import Any

LOG = logging.getLogger(__name__)

UnformattedResult = dict[str, Any]

profile_array_modifiers = {
    "staphylococcus_aureus": "saureus",
    "escherichia_coli": "ecoli",
    "klebsiella_pneumoniae": "kpneumoniae",
    "mycobacterium_tuberculosis": "mtuberculosis",
    "streptococcus_pyogenes": "spyogenes",
    "streptococcus": "streptococcus",
    "staphylococcus": "saureus",
}


def v1_to_v2(result: UnformattedResult) -> UnformattedResult:
    """Convert result in json format from v1 to v2."""
    input_schema_version = result["schema_version"]
    if input_schema_version != 1:
        raise ValueError(f"Invalid schema version '{input_schema_version}' expected 1")

    LOG.info("Migrating from v%d to v%d", input_schema_version, 2)
    upd_result = copy(result)
    # split analysis profile into a list and strip white space
    upd_profile: list[str] = [
        prof.strip() for prof in result["pipeline"]["analysis_profile"].split(",")
    ]
    upd_result["pipeline"]["analysis_profile"] = upd_profile
    # get assay from upd_profile
    new_assay: str | None = next(
        (
            profile_array_modifiers[prof]
            for prof in upd_profile
            if prof in profile_array_modifiers
        ),
        None,
    )
    if new_assay is None:
        raise ValueError(
            f"analysis_profile is not associated with a known assay, '{upd_profile}'"
        )
    upd_result["pipeline"]["assay"] = new_assay
    # add release_life_cycle
    new_release_life_cycle: str = (
        "development" if {"dev", "development"} & set(upd_profile) else "production"
    )
    upd_result["pipeline"]["release_life_cycle"] = new_release_life_cycle
    # update schema version
    upd_result["schema_version"] = 2
    return upd_result
