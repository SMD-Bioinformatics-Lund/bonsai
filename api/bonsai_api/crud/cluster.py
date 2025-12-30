"""Cluster related CRUD operations."""

import logging
from typing import Any, Sequence

from bonsai_api.crud.builder.summary import build_summary_entry_stages
from bonsai_api.crud.builder.types import BuilderArgs, PipelineStages
from bonsai_api.exceptions import EntryNotFound
from bonsai_api.db import Database
from bonsai_api.models.base import RWModel
from prp.parse.typing import replace_cgmlst_errors

LOG = logging.getLogger(__name__)


class TypingProfileAggregate(RWModel):  # pylint: disable=too-few-public-methods
    """Sample id and predicted alleles."""

    sample_id: str
    typing_result: dict[str, Any]

    def allele_profile(self, strip_errors: bool = True):
        """Get allele profile."""
        profile = {}
        for gene, allele in self.typing_result.items():
            if isinstance(allele, int):
                profile[gene] = allele
            elif isinstance(allele, str) and allele.startswith("*"):
                profile[gene] = int(allele[1:])
            elif strip_errors:
                profile[gene] = None
            else:
                profile[gene] = allele
        return profile


TypingProfileOutput = list[TypingProfileAggregate]


CLUSTER_TYPING_SPECS: dict[str, BuilderArgs] = {
    "mlst": BuilderArgs(
        selector={"software": "mlst", "type": "mlst"},
        source_path="typing_result",
        output="tool",
        output_field="typing_result",
        exclude_fields=[],  # keep alleles
    ),
    "cgmlst": BuilderArgs(
        selector={"software": "chewbbaca"},
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
    pipeline.extend(build_summary_entry_stages(spec))
    pipeline.append({"$addFields": {"typing_result": "$typing_result.alleles"}})
    pipeline.append({"$project": {"_id": 0, "sample_id": 1, "typing_result": 1}})

    # Query database
    results: list[TypingProfileAggregate] = []
    async for raw in db.sample_collection.aggregate(pipeline):
        loci_map = raw.get("typing_result") or {}
        results.append(
            TypingProfileAggregate(
                sample_id=raw["sample_id"],
                typing_result={
                    loci: replace_cgmlst_errors(
                        allele, include_novel_alleles=True, correct_alleles=True
                    )
                    for loci, allele in loci_map.items()
                },
            )
        )

    # Missing samples check (same semantics as before)
    found_ids = {s.sample_id for s in results}
    missing = set(sample_idx) - found_ids
    if missing:
        sample_ids = ", ".join(sorted(missing))
        raise EntryNotFound(
            f'The samples "{sample_ids}" didnt have {typing_method} typing result.'
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
) -> Sequence[str]:
    """Get genome signature paths for a samples stored in the database."""
    LOG.info("Get ska indexes for samples")
    query = {
        "$and": [  # query for documents with
            {"sample_id": {"$in": sample_ids}},  # matching sample ids
            {"ska_index": {"$ne": None}},  # AND genome_signatures not null
        ]
    }
    projection = {"_id": 0, "sample_id": 1, "ska_index": 1}
    LOG.debug("Query: %s; projection: %s", query, projection)
    cursor = db.sample_collection.find(query, projection)
    results = await cursor.to_list(None)
    LOG.debug("Found %d ska indexes", len(results))
    return results
