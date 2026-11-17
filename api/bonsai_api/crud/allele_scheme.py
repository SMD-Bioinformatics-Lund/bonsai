"""Verify producing profiles and, for MLST, detected schemes and locus sets."""

from collections.abc import Iterable, Mapping
from typing import Any, TYPE_CHECKING

from bonsai_api.models.allele_scheme import AlleleSchemeGroup, AlleleSchemeValidation

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
    """Use the sample name shown on basket cards, with legacy ID fallbacks."""
    return profile.sample_name or profile.external_sample_id or profile.sample_id


def summarize_sample_labels(labels: Iterable[str]) -> str:
    """Show five sample labels, one per row, and count remaining samples."""
    samples = sorted(labels)
    shown = samples[:5]
    if len(samples) > 5:
        shown.append(f"and {len(samples) - 5} more")
    return "\n".join(shown)


def _sample_detail(label: str, samples: Iterable[str]) -> str:
    """Keep the explanation above one sample per row."""
    rows = summarize_sample_labels(samples)
    return f"{label}:\n{rows}"


def _notice_group(label: str, profiles: "TypingProfileOutput") -> AlleleSchemeGroup:
    return AlleleSchemeGroup(
        detail=_sample_detail(label, (_sample_label(p) for p in profiles)),
        sample_ids=[p.sample_id for p in profiles],
    )


def _identity_groups(profiles: "TypingProfileOutput", field: str) -> list[AlleleSchemeGroup]:
    """Keep every category's IDs even when the displayed names are truncated."""
    groups: dict[str, TypingProfileOutput] = {}
    for profile in profiles:
        if value := getattr(profile, field):
            groups.setdefault(value, []).append(profile)
    return [
        _notice_group(
            f"{value} — {len(samples)} {'sample' if len(samples) == 1 else 'samples'}",
            samples,
        )
        for value, samples in sorted(groups.items())
    ]


def validate_typing_schemes(
    profiles: "TypingProfileOutput", typing_method: str
) -> AlleleSchemeValidation:
    """Validate selected profiles, assuming shared cgMLST loci within an assay."""
    name = "cgMLST" if typing_method == "cgmlst" else "MLST"
    identity = "analysis profile" if typing_method == "cgmlst" else "typing scheme"
    candidates = [p for p in profiles if p.typing_result]
    missing = [p for p in profiles if not p.typing_result]
    if missing:
        group = _notice_group(f"No {name} typing profile is available", missing)
        return AlleleSchemeValidation(
            can_cluster=False,
            notice=f"Cannot cluster by {name}: typing data is unavailable for {len(missing)} "
            f"{'sample' if len(missing) == 1 else 'samples'}. Remove these samples to continue.",
            details=[group.detail],
            groups=[group],
        )
    if not candidates or any(not p.scheme for p in candidates):
        unknown = [p for p in candidates if not p.scheme]
        reason = (
            "The analysis profile of the producing run is missing or ambiguous"
            if typing_method == "cgmlst"
            else "No detected MLST scheme is available"
        )
        groups = [_notice_group(reason, unknown)] if unknown else []
        return AlleleSchemeValidation(
            can_cluster=False,
            notice=(
                f"Cannot cluster by {name}: the {identity} "
                "could not be verified for every sample."
            ),
            details=[group.detail for group in groups],
            groups=groups,
        )
    schemes = {p.scheme for p in profiles if p.scheme}
    # For now, assume cgMLST uses the same loci within an analysis profile.
    locus_sets = (
        {frozenset(p.typing_result) for p in candidates}
        if typing_method == "mlst"
        else set()
    )
    if len(schemes) > 1 or len(locus_sets) > 1:
        notice_groups = []
        if len(schemes) > 1:
            notice_groups.extend(_identity_groups(profiles, "scheme"))
        elif len(locus_sets) > 1:
            locus_groups: dict[frozenset[str], TypingProfileOutput] = {}
            for profile in candidates:
                locus_groups.setdefault(frozenset(profile.typing_result), []).append(profile)
            for index, (loci, samples) in enumerate(locus_groups.items(), start=1):
                locus_names = ", ".join(sorted(loci))
                notice_groups.append(
                    _notice_group(
                        f"Locus set {index} ({len(loci)} loci; {locus_names})", samples
                    )
                )
        if len(schemes) > 1:
            selection = "profile" if typing_method == "cgmlst" else "scheme"
            notice = (
                f"Cannot cluster by {name}: the selected samples use different {identity}s. "
                f"Select samples from one {selection} to resolve this conflict."
            )
        else:
            notice = (
                "Cannot cluster by MLST: the selected samples share a typing scheme "
                "but have different locus sets. Check that their MLST results use "
                "the same locus definitions."
            )
        return AlleleSchemeValidation(
            can_cluster=False,
            notice=notice,
            details=[group.detail for group in notice_groups],
            groups=notice_groups,
        )
    if typing_method == "mlst":
        if any(not p.assay for p in candidates):
            group = _notice_group(
                "The analysis profile of the producing run is missing or ambiguous",
                [p for p in candidates if not p.assay],
            )
            return AlleleSchemeValidation(
                can_cluster=False,
                notice=(
                    "Cannot cluster by MLST: the analysis profile "
                    "could not be verified for every sample."
                ),
                details=[group.detail],
                groups=[group],
            )
        if len({p.assay for p in profiles if p.assay}) > 1:
            groups = _identity_groups(profiles, "assay")
            return AlleleSchemeValidation(
                can_cluster=False,
                notice=(
                    "Cannot cluster by MLST: the selected samples use different analysis profiles. "
                    "Select samples from one profile to resolve this conflict."
                ),
                details=[group.detail for group in groups],
                groups=groups,
            )
    return AlleleSchemeValidation(can_cluster=len(profiles) >= 2)
