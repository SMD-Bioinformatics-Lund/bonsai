"""Verify scheme identity and complete locus sets before allele comparison."""

import json
from collections.abc import Mapping
from typing import Any, TYPE_CHECKING

from bonsai_api.models.allele_scheme import AlleleSchemeValidation

if TYPE_CHECKING:
    from bonsai_api.crud.cluster import TypingProfileOutput


def get_profile_scheme(raw: Mapping[str, Any], typing_method: str) -> str | None:
    """Use declared identity and the database from this analysis's own pipeline run."""
    declared = raw.get("scheme")
    declared = (
        declared.strip() if isinstance(declared, str) and declared.strip() else None
    )
    if typing_method != "cgmlst":
        return declared
    run_id = raw.get("typing_pipeline_run_id")
    if not run_id:
        return declared
    runs = [
        run
        for run in (raw.get("pipeline_runs") or [])
        if isinstance(run, Mapping) and run.get("pipeline_run_id") == run_id
    ]
    if len(runs) != 1:
        return declared
    pipeline_info = runs[0].get("pipeline_info") or {}
    if not isinstance(pipeline_info, Mapping):
        return declared
    databases = [
        database
        for database in (pipeline_info.get("databases") or [])
        if isinstance(database, Mapping)
        and str(database.get("software", "")).lower() == "chewbbaca"
    ]
    if len(databases) != 1:
        return declared
    database = databases[0]
    name, version = database.get("name"), database.get("version")
    if (
        not isinstance(name, str)
        or not name.strip()
        or not isinstance(version, str)
        or not version.strip()
    ):
        return declared
    return json.dumps([declared, name.strip(), version.strip()], separators=(",", ":"))


def validate_typing_schemes(
    profiles: "TypingProfileOutput", typing_method: str
) -> AlleleSchemeValidation:
    """Validate the exact selected profiles; normalization must preserve locus keys."""
    name = "cgMLST" if typing_method == "cgmlst" else "MLST"
    candidates = [p for p in profiles if p.typing_result]
    if not candidates or any(not p.scheme for p in candidates):
        return AlleleSchemeValidation(
            can_cluster=False,
            notice=f"Cannot cluster by {name}: the typing scheme could not be verified for every sample.",
        )
    # Include identities from empty profiles when available, but do not infer
    # a locus definition from a profile that has no typing result.
    schemes = {p.scheme for p in profiles if p.scheme}
    locus_sets = {frozenset(p.typing_result) for p in candidates}
    if len(schemes) > 1 or len(locus_sets) > 1:
        return AlleleSchemeValidation(
            can_cluster=False,
            notice=f"Cannot cluster by {name}: the selected samples have different typing schemes or locus sets.",
        )
    return AlleleSchemeValidation(can_cluster=len(profiles) >= 2)
