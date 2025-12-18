"""Build sample summary and its manifest."""


from typing import Any

from .spec import BUILDER_REGISTRY
from bonsai_api.models.summary_manifest import Manifest, BuildOutput, PipelineProjection, PipelineStages


def _build_get_entry_stage(source_path: str, output_field: str, selector: dict[str, Any], default_result: dict[str, Any]) -> PipelineStages:
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
        return {"$in": [f"$$x.{k}", v]} if isinstance(v, list) else {"$eq": [f"$$x.{k}", v]}

    def _cond_for_obj(k: str, v: Any) -> dict[str, Any]:
        return {"$in": [f"${source_path}.{k}", v]} if isinstance(v, list) else {"$eq": [f"${source_path}.{k}", v]}

    array_conds = [{"$and": [_cond_for_array(k, v) for k, v in selector.items()]}] if selector else []
    obj_conds   = [{"$and": [_cond_for_obj(k, v)   for k, v in selector.items()]}] if selector else []

    # Build AND conditions for array items: "$$x.<key> == <value>"
    array_conds = [
        {"$eq": [ f"$$x.{fname}", val]} for fname, val in selector.items()
    ]

    # Build AND conditions for object: "$<source_path>.<key> == <value>"
    obj_conds = [
        {"$eq": [ f"${source_path}.{fname}", val]} for fname, val in selector.items()
    ]
    default_entry = { **selector, "result": default_result }
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
                                        { "$isArray": f"${source_path}" },
                                        f"${source_path}",
                                        []  # not an array -> empty
                                    ]
                                },
                                "as": "x",
                                "cond": { "$and": array_conds[0] } if array_conds else True,
                            }
                        },
                        0
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
                        None
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
                            "$ifNull": [ f"$__{output_field}_sel_array", f"$__{output_field}_sel_obj" ],
                        },
                        default_entry
                    ]
                }
            }
        },
        { "$unset": [ f"__{output_field}_sel_array", f"__{output_field}_sel_obj" ] }
    ]


def _build_flatten_results_stage(field_name: str, *, label_field: str | None = "software", static_prefix: str | None = None) -> PipelineStages:
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
            {"$toLower": { "$ifNull": [ f"${field_name}.{label_field}", field_name ] }}
            if label_field else field_name
        )
    )
    return [
        {
            "$set": { 
                f"{field_name}_prefixed": { 
                    "$map": {
                        "input": { "$objectToArray": { "$ifNull": [ f"${field_name}.result", {} ] } },
                        "as": "kv",
                        "in": {
                            "k": { "$concat": [ prefix_expr, "_", "$$kv.k" ] },
                            "v": "$$kv.v"
                        }
                    }
                }
            }
        },
        {
            "$set": { 
                f"{field_name}_merged": { 
                    "$arrayToObject": { "$ifNull": [ f"${field_name}_prefixed", [] ] }
                }
            }
        },
        {
            "$replaceRoot": {
                "newRoot": { "$mergeObjects": [ "$$ROOT", f"${field_name}_merged" ] }
            }
        },
        { "$unset": [ f"{field_name}_prefixed", f"{field_name}_merged", field_name ] }
    ]


def _build_result_summary(
        *, 
        source_path: str, 
        selector: dict[str, Any], 
        output_field: str | None = None,
        hit: int = 0,
        output: BuildOutput = "both", 
        exclude_fields: list[str] | None = None, 
        label_field: str | None = "software",
        static_prefix: str | None = None,
        default_result: Any = []
        ) -> PipelineStages:
    """
    Normalize a tool entry that may live in `source_path` as either an array of entries
    or a single object. Each entry has the shape: { software: <str>, result: <array|object> }.

    Steps:
      1) Select the entry from `source_path` (array or object) that matches `selector`.
      2) Normalize `<output_field>.result` to a single object:
         - if array → take the `hit`-th element (guarded), else {}
         - if object → use as-is (or {} if null)
      3) Optionally remove keys from the normalized result (`exclude_fields`).
      4) Emit:
         - "tool": keep only the normalized result under `<output_field>`
         - "root": flatten to `<prefix>_*` at root (and remove `<output_field>`)
         - "both": flatten to root AND keep `<output_field>` entry
    """
    # If not provided, default the output field to selector[label_field] or the source name.
    of = output_field or selector.get(label_field or "", source_path)

    stages: PipelineStages = []
    stages.extend(_build_get_entry_stage(
        source_path=source_path, output_field=of, selector=selector, default_result=default_result
    ))
    # If the result is an array, pick the n-th element else use as is

   # 2) Normalize `result` to one object
    stages.append({
        "$addFields": {
            f"{of}.result": {
                "$cond": [
                    {"$isArray": f"${of}.result"},
                    {"$cond": [
                        { "$gt": [ { "$size": { "$ifNull": [ f"${of}.result", [] ] } }, hit ] },
                        { "$arrayElemAt": [ f"${of}.result", hit ] },
                        {}
                    ]},
                    { "$ifNull": [ f"${of}.result", {} ] },
                ]
            }
        }
    })

    # 3) Exclude fields
    if exclude_fields:
        stages.append({ "$unset": [ f"{of}.result.{e}" for e in exclude_fields ] })

    # 4) Emit
    if output in ("root", "both"):
        stages += _build_flatten_results_stage(of, label_field=label_field, static_prefix=static_prefix)
        if output == "root":
            stages.append({ "$unset": [ of ] })

    if output == "tool":
        stages.append({ "$addFields": { of: { "$ifNull": [ f"${of}.result", {} ] } } })
    return stages


def compile_pipeline(manifest: Manifest, fields: list[str] | None = None) -> list[dict[str, Any]]:
    """Compile aggregation pipeline from the manifest."""

    pipeline: PipelineStages = []
    project: PipelineProjection = {"_id": 0}

    drop_after_build = set()
    used_builders = []
    for col in manifest.columns:
        # Dont build stage if it is not requested
        if fields and set(fields).isdisjoint([col.id]):
            continue

        for builder_name in col.requires:
            # skip if builder has already been added
            if builder_name in used_builders:
                continue

            if (build_args := BUILDER_REGISTRY.get(builder_name)) is None:
                raise RuntimeError(f"Unkown build function: {builder_name}")
            
            pipeline.extend(_build_result_summary(**build_args.model_dump()))

            output_field = (build_args.output_field or build_args.source_path)
            drop_after_build.add(output_field)

            used_builders.append(builder_name)

        # Build how to display the result
        project[col.id] = col.path

    # Drop large sub-documents when pipeline stages has been built
    if drop_after_build:
        pipeline.append({"$unset": list(drop_after_build)})
    
    pipeline.append({"$project": project})
    #pipeline.append({"$project": {'_id': 0}})
    return pipeline
