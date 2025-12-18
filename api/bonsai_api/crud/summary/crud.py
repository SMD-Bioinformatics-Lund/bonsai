"""Summary crud functions"""
from typing import Any
from bonsai_api.models.summary_manifest import SummaryConfig
from bonsai_api.models.base import MultipleRecordsResponseModel
from pymongo import ASCENDING, DESCENDING
from bonsai_api.db import Database


from .compile import compile_pipeline


async def get_samples_summary(
    db: Database,
    config: SummaryConfig,
    *,
    match: dict[str, Any],
    fields: list[str] | None,
    sort: str,
    limit: int,
    offset: int | None = None,
    cursor: str | None = None,
):
    """Get summarized sample information."""
    pipeline: list[dict[str, Any]] = []
    if match:
        pipeline.append({"$match": match})

    # add stable sorting to facilitate offset
    sort_fields = "-created_at" if not sort else sort
    sort_dir = DESCENDING if sort_fields.startswith("-") else ASCENDING
    key = sort_fields[1:] if sort_fields.startswith("-") else sort_fields
    allowed_sort_fields = {
        "created_at": "created_at",
        "modified_at": "modified_at",
        "id": "_id",
        "sample_id": "sample_id",
    }
    if key not in allowed_sort_fields:
        raise ValueError(f"Unsupported sort: {key}")
    pipeline.append({"$sort": {allowed_sort_fields[key]: sort_dir}})

    pipeline.extend(compile_pipeline(config, fields))

    # manage skip, limit and offset
    data_pipe: list[dict[str, Any]] = []
    if offset and offset > 0:
        data_pipe.append({"$skip": offset})
    if limit and limit > 0:
        data_pipe.append({"$limit": limit})

    pipeline.append(
        {
            "$facet": {
                "data": data_pipe or [{"$match": match}],
                "records_total": [{"$count": "count"}],
            }
        },
    )

    # query database for the number of samples
    cursor = await db.sample_collection.aggregate(pipeline)
    res = await cursor.to_list(None)
    if not res:
        return MultipleRecordsResponseModel(data=[], records_total=0)
    facet = res[0]
    total = (
        0 if not facet.get("records_total") else facet["records_total"][0].get("count")
    )
    return MultipleRecordsResponseModel(data=facet["data"], records_total=total)