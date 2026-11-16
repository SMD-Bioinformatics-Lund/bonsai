"""Verify method-specific identity and complete locus sets before comparison."""

from collections.abc import Mapping
from typing import Any, TYPE_CHECKING

from bonsai_api.models.allele_scheme import AlleleSchemeValidation

if TYPE_CHECKING:
    from bonsai_api.crud.cluster import TypingProfileAggregate, TypingProfileOutput


def get_profile_scheme(raw: Mapping[str, Any], typing_method: str) -> str | None:
    """Use the detected MLST scheme or the producing cgMLST run's assay/profile."""
    if typing_method != "cgmlst":
        declared = raw.get("scheme")
        return (
            declared.strip() if isinstance(declared, str) and declared.strip() else None
        )
    # Each cgMLST assay currently defines one compatible scheme. Database and
    # software versions can change without changing that compatibility identity.
    return get_profile_assay(raw)


def get_profile_assay(raw: Mapping[str, Any]) -> str | None:
    """Get the assay of the unambiguous run that produced the selected result."""
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
    assay = runs[0].get("assay")
    return assay.strip() if isinstance(assay, str) and assay.strip() else None


def _sample_label(profile: "TypingProfileAggregate") -> str:
    """Prefer the Lab ID in validation details."""
    return profile.external_sample_id or profile.sample_id


def _identity_details(profiles: "TypingProfileOutput", field: str, label: str) -> list[str]:
    """Show which samples belong to each known compatibility identity."""
    groups: dict[str, list[str]] = {}
    for profile in profiles:
        if value := getattr(profile, field):
            groups.setdefault(value, []).append(_sample_label(profile))
    return [
        f"{label} {value}: {', '.join(sorted(samples))}."
        for value, samples in sorted(groups.items())
    ]


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
            details=[
                f"{_sample_label(p)}: "
                + (
                    "the analysis profile of the producing run is missing or ambiguous."
                    if typing_method == "cgmlst"
                    else "no detected MLST scheme is available."
                )
                for p in candidates
                if not p.scheme
            ],
        )
    # Include identities from empty profiles when available, but do not infer
    # a locus definition from a profile that has no typing result.
    schemes = {p.scheme for p in profiles if p.scheme}
    locus_sets = {frozenset(p.typing_result) for p in candidates}
    if len(schemes) > 1 or len(locus_sets) > 1:
        details = []
        if len(schemes) > 1:
            details.extend(_identity_details(profiles, "scheme", identity.capitalize()))
        if len(locus_sets) > 1:
            groups: dict[frozenset[str], list[str]] = {}
            for profile in candidates:
                groups.setdefault(frozenset(profile.typing_result), []).append(
                    _sample_label(profile)
                )
            for index, (loci, samples) in enumerate(groups.items(), start=1):
                examples = ", ".join(sorted(loci)[:5])
                if len(loci) > 5:
                    examples += ", …"
                details.append(
                    f"Locus set {index} ({len(loci)} loci; {examples}): "
                    f"{', '.join(sorted(samples))}."
                )
        return AlleleSchemeValidation(
            can_cluster=False,
            notice=f"Cannot cluster by {name}: the selected samples have different {identity}s or locus sets.",
            details=details,
        )
    if typing_method == "mlst":
        if any(not p.assay for p in candidates):
            return AlleleSchemeValidation(
                can_cluster=False,
                notice="Cannot cluster by MLST: the analysis profile could not be verified for every sample.",
                details=[
                    f"{_sample_label(p)}: the analysis profile of the producing run is missing or ambiguous."
                    for p in candidates
                    if not p.assay
                ],
            )
        if len({p.assay for p in profiles if p.assay}) > 1:
            return AlleleSchemeValidation(
                can_cluster=False,
                notice="Cannot cluster by MLST: the selected samples have different analysis profiles.",
                details=_identity_details(profiles, "assay", "Analysis profile"),
            )
    return AlleleSchemeValidation(can_cluster=len(profiles) >= 2)
