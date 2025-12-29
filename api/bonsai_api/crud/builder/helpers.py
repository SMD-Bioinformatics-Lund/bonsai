"""Pipeline builder helper functions."""

from typing import Any

from bonsai_api.db import Database
from pymongo import ASCENDING, DESCENDING

from .types import LookupSpec, PipelineStage, PipelineStages


def build_get_entry_stage(
    source_path: str,
    output_field: str,
    selector: dict[str, Any],
    default_result: dict[str, Any],
) -> PipelineStages:
    """
    Select a single entry from `source_path` (which may be an array or an object)
    where all key/value pairs in `selector` match.

    - If `source_path` is an array: find first item `x` where all `selector` fields match.
    - If `source_path` is an object: use it iff it matches `selector`.
    - If nothing matches: emit a default entry `{**selector, result: default_result}`.

    Supports simple equality and `$in` via passing list values in `selector`.
    """

    def _cond_for_array(k: str, v: Any) -> dict[str, Any]:
        # list -> `$in`, else `$eq`
        return (
            {"$in": [f"$$x.{k}", v]}
            if isinstance(v, list)
            else {"$eq": [f"$$x.{k}", v]}
        )

    def _cond_for_obj(k: str, v: Any) -> dict[str, Any]:
        return (
            {"$in": [f"${source_path}.{k}", v]}
            if isinstance(v, list)
            else {"$eq": [f"${source_path}.{k}", v]}
        )

    array_conds = (
        [{"$and": [_cond_for_array(k, v) for k, v in selector.items()]}]
        if selector
        else []
    )
    obj_conds = (
        [{"$and": [_cond_for_obj(k, v) for k, v in selector.items()]}]
        if selector
        else []
    )

    # Build AND conditions for array items: "$$x.<key> == <value>"
    array_conds = [{"$eq": [f"$$x.{fname}", val]} for fname, val in selector.items()]

    # Build AND conditions for object: "$<source_path>.<key> == <value>"
    obj_conds = [
        {"$eq": [f"${source_path}.{fname}", val]} for fname, val in selector.items()
    ]
    default_entry = {**selector, "result": default_result}
    return [
        # Try to select from an array
        {
            "$set": {
                f"__{output_field}_sel_array": {
                    "$arrayElemAt": [
                        {
                            "$filter": {
                                "input": {
                                    "$cond": [
                                        {"$isArray": f"${source_path}"},
                                        f"${source_path}",
                                        [],  # not an array -> empty
                                    ]
                                },
                                "as": "x",
                                "cond": (
                                    {"$and": array_conds[0]} if array_conds else True
                                ),
                            }
                        },
                        0,
                    ]
                }
            }
        },
        # I its an object and matches, use the object entry
        {
            "$set": {
                f"__{output_field}_sel_obj": {
                    "$cond": [
                        {
                            "$and": [
                                {"$not": {"$isArray": f"{source_path}"}},
                                {"$ne": [f"{source_path}", None]},
                                obj_conds[0] if obj_conds else True,
                            ]
                        },
                        f"{source_path}",
                        None,
                    ]
                }
            }
        },
        # Choose array match, else obj match else the default object
        {
            "$set": {
                output_field: {
                    "$ifNull": [
                        {
                            "$ifNull": [
                                f"$__{output_field}_sel_array",
                                f"$__{output_field}_sel_obj",
                            ],
                        },
                        default_entry,
                    ]
                }
            }
        },
        {"$unset": [f"__{output_field}_sel_array", f"__{output_field}_sel_obj"]},
    ]


def build_flatten_results_stage(
    field_name: str,
    *,
    label_field: str | None = "software",
    static_prefix: str | None = None,
) -> PipelineStages:
    """
    Flatten `<field_name>.result` object into `<prefix>_*` keys at root.
    `prefix` is:
      - `static_prefix` if provided,
      - else `lower(<field_name>.<label_field>)` if label_field is set,
      - else `field_name` as a fallback.
    """
    prefix_expr = (
        static_prefix
        if static_prefix is not None
        else (
            {"$toLower": {"$ifNull": [f"${field_name}.{label_field}", field_name]}}
            if label_field
            else field_name
        )
    )
    return [
        {
            "$set": {
                f"{field_name}_prefixed": {
                    "$map": {
                        "input": {
                            "$objectToArray": {"$ifNull": [f"${field_name}.result", {}]}
                        },
                        "as": "kv",
                        "in": {
                            "k": {"$concat": [prefix_expr, "_", "$$kv.k"]},
                            "v": "$$kv.v",
                        },
                    }
                }
            }
        },
        {
            "$set": {
                f"{field_name}_merged": {
                    "$arrayToObject": {"$ifNull": [f"${field_name}_prefixed", []]}
                }
            }
        },
        {
            "$replaceRoot": {
                "newRoot": {"$mergeObjects": ["$$ROOT", f"${field_name}_merged"]}
            }
        },
        {"$unset": [f"{field_name}_prefixed", f"{field_name}_merged", field_name]},
    ]


def build_lookup_stage(db: Database, spec: LookupSpec) -> PipelineStages:
    """LOOKUP stage builder."""
    stages: PipelineStages = []

    collection = getattr(db, spec.from_collection, None)
    if collection is None:
        raise RuntimeError(
            f"Cannot build lookup: unknown collection '{spec.from_collection}'"
        )

    # Prefer pipeline form if provided
    if spec.pipeline:
        stages.append(
            {
                "$lookup": {
                    "from": collection.name,
                    "let": spec.let or {},
                    "pipeline": spec.pipeline,
                    "as": spec.as_field,
                }
            }
        )
    else:
        # Fall back to simple equality lookup
        if spec.local_field is None or spec.foreign_field is None:
            raise ValueError(
                "local_field and foreign_field are required for simple $lookup"
            )
        stages.append(
            {
                "$lookup": {
                    "from": collection.name,
                    "localField": spec.local_field,
                    "foreignField": spec.foreign_field,
                    "as": spec.as_field,
                }
            }
        )

    if spec.add_fields:
        stages.append({"$addFields": spec.add_fields})
    if spec.project:
        stages.append({"$project": spec.project})

    return stages


def build_sort_stage(sort: str, allowed_fields: set[str]) -> PipelineStage:
    """Build a $sort stage from a sort string like '-created_at'."""
    sort_dir = DESCENDING if sort.startswith("-") else ASCENDING
    sort_expr = sort[1:] if sort.startswith("-") else sort

    if sort_expr not in allowed_fields:
        raise ValueError(f"Unsupported sort: {sort_expr}")

    return {"$sort": {sort_expr: sort_dir, "_id": 1}}


def build_skip_limit(offset: int = 0, limit: int | None = None) -> PipelineStages:
    """Build skip/ limit stages."""
    stages: PipelineStages = []
    if offset and offset > 0:
        stages.append({"$skip": offset})
    if limit and limit > 0:
        stages.append({"$limit": limit})
    return stages


def build_facet_pagination(offset: int = 0, limit: int | None = None) -> PipelineStage:
    """Build a $facet stage for unified pagination."""
    data_pipeline = build_skip_limit(offset, limit)
    return {"$facet": {"data": data_pipeline, "records_total": [{"$count": "count"}]}}
