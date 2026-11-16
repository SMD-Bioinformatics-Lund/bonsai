"""Verify method-specific identity and complete locus sets before comparison."""

from collections.abc import Mapping
from typing import Any, TYPE_CHECKING

from bonsai_api.models.allele_scheme import AlleleSchemeValidation

if TYPE_CHECKING:
    from bonsai_api.crud.cluster import TypingProfileOutput


def get_profile_scheme(raw: Mapping[str, Any], typing_method: str) -> str | None:
    """Use the detected MLST scheme or the producing cgMLST run's assay/profile."""
    if typing_method != "cgmlst":
        declared = raw.get("scheme")
        return (
            declared.strip() if isinstance(declared, str) and declared.strip() else None
        )
    run_id = raw.get("typing_pipeline_run_id")
    if not run_id:
        return None
    runs = [
        run
        for run in (raw.get("pipeline_runs") or [])
        if isinstance(run, Mapping) and run.get("pipeline_run_id") == run_id
    ]
    if len(runs) != 1:
        return None
    # Each cgMLST assay currently defines one compatible scheme. Database and
    # software versions can change without changing that compatibility identity.
    assay = runs[0].get("assay")
    return assay.strip() if isinstance(assay, str) and assay.strip() else None


def validate_typing_schemes(
    profiles: "TypingProfileOutput", typing_method: str
) -> AlleleSchemeValidation:
    """Validate the exact selected profiles; normalization must preserve locus keys."""
    name = "cgMLST" if typing_method == "cgmlst" else "MLST"
    identity = "analysis profile" if typing_method == "cgmlst" else "typing scheme"
    candidates = [p for p in profiles if p.typing_result]
    if not candidates or any(not p.scheme for p in candidates):
        return AlleleSchemeValidation(
            can_cluster=False,
            notice=f"Cannot cluster by {name}: the {identity} could not be verified for every sample.",
        )
    # Include identities from empty profiles when available, but do not infer
    # a locus definition from a profile that has no typing result.
    schemes = {p.scheme for p in profiles if p.scheme}
    locus_sets = {frozenset(p.typing_result) for p in candidates}
    if len(schemes) > 1 or len(locus_sets) > 1:
        return AlleleSchemeValidation(
            can_cluster=False,
            notice=f"Cannot cluster by {name}: the selected samples have different {identity}s or locus sets.",
        )
    return AlleleSchemeValidation(can_cluster=len(profiles) >= 2)
