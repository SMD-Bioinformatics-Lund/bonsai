"""Cluster related CRUD operations."""

import json
import logging
from collections.abc import Mapping, Sequence
from itertools import combinations
from typing import Any

from bonsai_libs.parse.parsers.chewbacca import replace_cgmlst_errors

from bonsai_api.crud.builder.summary import build_summary_entry_stages
from bonsai_api.crud.builder.types import BuilderArgs, PipelineStages
from bonsai_api.db import Database
from bonsai_api.exceptions import EntryNotFound, InvalidDataFormat
from bonsai_api.models.allele_cluster import AlleleClusterValidation, UnplacedSample
from bonsai_api.models.base import RWModel
from bonsai_api.redis.models import SkaIndexInput

LOG = logging.getLogger(__name__)


def get_sample_label(sample: Mapping[str, Any] | None, sample_id: str) -> str:
    """Return the Lab ID when available, falling back to the internal ID."""
    if sample and isinstance(sample.get("external_sample_id"), str):
        external_sample_id = sample["external_sample_id"]
        if external_sample_id:
            return external_sample_id
    return sample_id


class TypingProfileAggregate(RWModel):  # pylint: disable=too-few-public-methods
    """Sample id and predicted alleles."""

    sample_id: str
    typing_result: dict[str, Any]
    label: str | None = None
    scheme: str | None = None

    def allele_profile(self, strip_errors: bool = True):
        """Get allele profile."""
        profile = {}
        for gene, allele in self.typing_result.items():
            if type(allele) is int:
                profile[gene] = allele if allele > 0 else None
            elif isinstance(allele, str) and allele.lstrip("*").isdecimal():
                value = int(allele.lstrip("*"))
                profile[gene] = value if value > 0 else None
            elif strip_errors:
                profile[gene] = None
            else:
                profile[gene] = allele
        return profile


TypingProfileOutput = list[TypingProfileAggregate]


def get_unplaced_samples(profiles: TypingProfileOutput) -> list[UnplacedSample]:
    """Account for samples that cannot contribute any called alleles."""
    return [
        UnplacedSample(
            sample_id=profile.sample_id, label=profile.label or profile.sample_id
        )
        for profile in profiles
        if not any(value is not None for value in profile.allele_profile().values())
    ]


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


def validate_typing_profiles(
    profiles: TypingProfileOutput, typing_method: str
) -> AlleleClusterValidation:
    """Require matching scheme identities and locus definitions before comparison."""
    unplaced = get_unplaced_samples(profiles)
    candidates = [profile for profile in profiles if profile.typing_result]
    profile_name = "cgMLST" if typing_method == "cgmlst" else "MLST"
    notice = None
    if any(not profile.scheme for profile in candidates):
        notice = (
            f"Cannot cluster by {profile_name}: the typing scheme could not be verified "
            "for every sample."
        )
    elif (
        len({profile.scheme for profile in profiles if profile.scheme}) > 1
        or len({frozenset(profile.typing_result) for profile in candidates}) > 1
    ):
        notice = (
            f"Cannot cluster by {profile_name}: the selected samples have different "
            "typing schemes or locus sets."
        )
    elif len(unplaced) == len(profiles):
        notice = f"Cannot cluster by {profile_name}: no selected sample has usable allele calls."
    else:
        called_loci = [
            {
                gene
                for gene, value in profile.allele_profile().items()
                if value is not None
            }
            for profile in profiles
        ]
        called_loci = [loci for loci in called_loci if loci]
        if any(a.isdisjoint(b) for a, b in combinations(called_loci, 2)):
            notice = f"Cannot cluster by {profile_name}: some sample pairs have no jointly called loci."
    return AlleleClusterValidation(
        can_cluster=notice is None and len(profiles) >= 2,
        notice=notice,
        unplaced_samples=unplaced,
    )


CLUSTER_TYPING_SPECS: dict[str, BuilderArgs] = {
    "mlst": BuilderArgs(
        selector={"software": "mlst", "analysis_type": "mlst"},
        source_path="typing_result",
        output="tool",
        output_field="typing_result",
        exclude_fields=[],  # keep alleles
    ),
    "cgmlst": BuilderArgs(
        selector={"software": "chewbbaca", "analysis_type": "cgmlst"},
        source_path="typing_result",
        output="tool",
        output_field="typing_result",
        exclude_fields=[],  # keep alleles
    ),
}


async def get_typing_profiles(
    db: Database, sample_idx: list[str], typing_method: str
) -> TypingProfileOutput:
    """Get locations from database."""
    spec = CLUSTER_TYPING_SPECS.get(typing_method)
    if spec is None:
        raise ValueError(f"Unsupported typing method: {typing_method}")

    pipeline: PipelineStages = []
    pipeline.append({"$match": {"sample_id": {"$in": sample_idx}}})
    stages = build_summary_entry_stages(spec)
    # Capture scheme metadata before the builder reduces the entry to its result.
    stages.insert(
        -1,
        {
            "$set": {
                "typing_pipeline_run_id": "$typing_result.pipeline_run_id",
                "cluster_scheme": {
                    "$ifNull": [
                        "$typing_result.result.scheme",
                        "$typing_result.meta.scheme",
                    ]
                },
            }
        },
    )
    pipeline.extend(stages)
    pipeline.append({"$addFields": {"typing_result": "$typing_result.alleles"}})
    # The external ID is projected only for user-facing validation errors.
    pipeline.append(
        {
            "$project": {
                "_id": 0,
                "sample_id": 1,
                "external_sample_id": 1,
                "typing_result": 1,
                "scheme": "$cluster_scheme",
                "typing_pipeline_run_id": 1,
                "pipeline_runs": 1,
            }
        }
    )

    # Query database
    results: list[TypingProfileAggregate] = []
    sample_labels: dict[str, str] = {}
    cursor = await db.sample_collection.aggregate(pipeline)
    async for raw in cursor:
        sample_labels[raw["sample_id"]] = get_sample_label(raw, raw["sample_id"])
        loci_map = raw.get("typing_result") or {}
        if not isinstance(loci_map, dict):
            raise InvalidDataFormat(
                f"Invalid {typing_method} allele profile for {sample_labels[raw['sample_id']]}"
            )
        normalized = {}
        for loci, allele in loci_map.items():
            if allele is None or isinstance(allele, list):
                normalized[loci] = None
                continue
            try:
                normalized[loci] = replace_cgmlst_errors(
                    allele, include_novel_alleles=True, correct_alleles=True
                )
            except (ValueError, IndexError, TypeError) as error:
                raise InvalidDataFormat(
                    f"Invalid {typing_method} allele call at {loci} for "
                    f"{sample_labels[raw['sample_id']]}"
                ) from error
        results.append(
            TypingProfileAggregate(
                sample_id=raw["sample_id"],
                typing_result=normalized,
                label=sample_labels[raw["sample_id"]],
                scheme=get_profile_scheme(raw, typing_method),
            )
        )

    # Existing samples without callable profiles are retained as unplaced samples.
    found_ids = {sample.sample_id for sample in results}
    missing = set(sample_idx) - found_ids
    if missing:
        missing_labels = ", ".join(
            sorted(sample_labels.get(sample_id, sample_id) for sample_id in missing)
        )
        profile_name = "cgMLST" if typing_method == "cgmlst" else typing_method.upper()
        raise EntryNotFound(
            f"No {profile_name} typing profile is available for the following samples: "
            f"{missing_labels}"
        )
    return results


async def get_signature_path_for_samples(
    db: Database, sample_ids: list[str]
) -> TypingProfileOutput:
    """Get genome signature paths for samples."""
    LOG.info("Get signatures for samples")
    query = {
        "$and": [  # query for documents with
            {"sample_id": {"$in": sample_ids}},  # matching sample ids
            {"genome_signature": {"$ne": None}},  # AND genome_signatures not null
        ]
    }
    projection = {"_id": 0, "sample_id": 1, "genome_signature": 1}  # projection
    LOG.debug("Query: %s; projection: %s", query, projection)
    cursor = db.sample_collection.find(query, projection)
    results = await cursor.to_list(None)
    LOG.debug("Found %d signatures", len(results))
    return results


async def get_ska_index_path_for_samples(
    db: Database, sample_ids: Sequence[str]
) -> list[SkaIndexInput]:
    """Get SKA indexes for samples, rejecting samples without an index."""
    LOG.info("Get ska indexes for samples")
    query = {"sample_id": {"$in": sample_ids}}
    projection = {
        "_id": 0,
        "sample_id": 1,
        "external_sample_id": 1,
        "ska_index": 1,
    }
    LOG.debug("Query: %s; projection: %s", query, projection)
    cursor = db.sample_collection.find(query, projection)
    results = await cursor.to_list(None)
    LOG.debug("Found %d ska indexes", len(results))

    samples_by_id = {sample["sample_id"]: sample for sample in results}
    missing_ids = [
        sample_id
        for sample_id in sample_ids
        if not samples_by_id.get(sample_id, {}).get("ska_index")
    ]
    if missing_ids:
        sample_labels = ", ".join(
            sorted(
                get_sample_label(samples_by_id.get(sample_id), sample_id)
                for sample_id in missing_ids
            )
        )
        raise EntryNotFound(
            "No SKA index is available for the following samples: " f"{sample_labels}"
        )

    return [
        SkaIndexInput(
            sample_id=sample_id,
            external_sample_id=get_sample_label(samples_by_id[sample_id], sample_id),
            ska_index=samples_by_id[sample_id]["ska_index"],
        )
        for sample_id in sample_ids
    ]
