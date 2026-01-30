"""Build queries for normalizing jasen results."""

import logging

from bonsai_api.db import Database

from .helpers import (
    build_flatten_results_stage,
    build_get_entry_stage,
    build_lookup_stage,
)
from .summary_manifest import BUILDER_REGISTRY
from .types import BuilderArgs, LookupSpec, Manifest, PipelineProjection, PipelineStages

LOG = logging.getLogger(__name__)


def build_summary_entry_stages(spec: BuilderArgs) -> PipelineStages:
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
    of = spec.output_field or spec.selector.get(
        spec.label_field or "", spec.source_path
    )
    default_result = spec.default_result or []

    stages: PipelineStages = []
    stages.extend(
        build_get_entry_stage(
            source_path=spec.source_path,
            output_field=of,
            selector=spec.selector,
            default_result=default_result,
        )
    )
    # If the result is an array, pick the n-th element else use as is

    # 2) Normalize `result` to one object
    stages.append(
        {
            "$addFields": {
                f"{of}.result": {
                    "$cond": [
                        {"$isArray": f"${of}.result"},
                        {
                            "$cond": [
                                {
                                    "$gt": [
                                        {"$size": {"$ifNull": [f"${of}.result", []]}},
                                        spec.hit,
                                    ]
                                },
                                {"$arrayElemAt": [f"${of}.result", spec.hit]},
                                {},
                            ]
                        },
                        {"$ifNull": [f"${of}.result", {}]},
                    ]
                }
            }
        }
    )

    # 3) Exclude fields
    if spec.exclude_fields:
        stages.append({"$unset": [f"{of}.result.{e}" for e in spec.exclude_fields]})

    # 4) Emit
    if spec.output in ("root", "both"):
        stages += build_flatten_results_stage(
            of, label_field=spec.label_field, static_prefix=spec.static_prefix
        )
        if spec.output == "root":
            stages.append({"$unset": [of]})

    if spec.output == "tool":
        stages.append({"$addFields": {of: {"$ifNull": [f"${of}.result", {}]}}})
    return stages


def compile_summary_pipeline(
    db: Database, manifest: Manifest, fields: list[str] | None = None
) -> PipelineStages:
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

            if (spec := BUILDER_REGISTRY.get(builder_name)) is None:
                raise RuntimeError(f"Unkown build function: {builder_name}")

            LOG.debug(
                "Building summary for column '%s' using builder '%s'",
                col.id,
                builder_name,
            )
            if isinstance(spec, BuilderArgs):
                pipeline.extend(build_summary_entry_stages(spec))
                output_field = spec.output_field or spec.source_path
                drop_after_build.add(output_field)
            elif isinstance(spec, LookupSpec):
                # run lookup function
                pipeline.extend(build_lookup_stage(spec=spec, db=db))
            else:
                raise RuntimeError(f"Dont know how to process: {spec}")

            used_builders.append(builder_name)

        # Build how to display the result
        project[col.id] = col.path

    # Drop large sub-documents when pipeline stages has been built
    if drop_after_build:
        pipeline.append({"$unset": list(drop_after_build)})

    pipeline.append({"$project": project})
    return pipeline
