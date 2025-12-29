"""Summary crud functions"""
import logging
from typing import Any

from .builder.types import Manifest
from .builder.summary import compile_summary_pipeline
from .builder.helpers import build_facet_pagination, build_sort_stage
from bonsai_api.models.base import MultipleRecordsResponseModel
from bonsai_api.db import Database


LOG = logging.getLogger(__name__)


async def get_samples_summary(
    db: Database,
    manifest: Manifest,
    *,
    match: dict[str, Any],
    fields: list[str] | None,
    sort: str,
    limit: int,
    offset: int | None = None,
):
    """Get summarized sample information."""
    if fields and (valid_fields := {col.id for col in manifest.columns}):
        invalid_fields = set(fields) - valid_fields
        if invalid_fields:
            err_info = ", ".join(list(invalid_fields))
            raise ValueError(f"Invalid fields: {err_info}")

    pipeline: list[dict[str, Any]] = []
    if match:
        pipeline.append({"$match": match})

    pipeline.extend(compile_summary_pipeline(db, manifest, fields))

    # add stable sorting to facilitate offset
    sort_fields = "-created_at" if not sort else sort
    pipeline.append(
        build_sort_stage(sort_fields, {col.id for col in manifest.columns if col.sortable})
    )

    # Pagination
    pipeline.append(build_facet_pagination(offset=offset, limit=limit))

    # query database for the number of samples
    agg_cursor = await db.sample_collection.aggregate(pipeline)
    results = await agg_cursor.to_list(None)

    if not results:
        return MultipleRecordsResponseModel(data=[], records_total=0)
    facet = results[0]
    total_list = facet.get("records_total", [])
    records_total = total_list[0]["count"] if total_list else 0

    return MultipleRecordsResponseModel(data=facet.get('data', []), records_total=records_total)
