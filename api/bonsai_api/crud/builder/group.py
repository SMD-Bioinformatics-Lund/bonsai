"""Build group related aggregation pipelines."""

from .types import PipelineProjection, PipelineStage, PipelineStages


def group_project_stage(
    include_presets: bool = True, include_allowed: bool = True
) -> PipelineProjection:
    """Build a projection stage for basic group info.

    - include_presets: whether to include column presets in the projection.
    - include_allowed: whether to include allowed_columns in the projection.
    """
    projection = {
        "_id": 0,
        "group_id": "$core.group_id",
        "display_name": "$core.display_name",
        "description": "$core.description",
        "sample_count": "$core.sample_count",
        "created_at": "$created_at",
        "modified_at": "$modified_at",
    }
    if include_presets:
        projection["default_preset_id"] = "$presets.default_preset_id"
        projection["presets"] = "$presets.items"
    if include_allowed:
        projection["table_columns"] = "$allowed_columns.column_ids"
    return {"$project": projection}


def build_group_visibility_match_stage(user_id: str) -> PipelineStage:
    """Build a $match stage to filter groups based on visibility."""
    return {
        "$match": {
            "$or": [
                {"core.visibility": "public"},
                {
                    "core.visibility": {"$exists": False}
                },  # treat missing visibility as public
                {"core.owner_id": user_id},
                {"invited_users": user_id},
            ]
        }
    }


def build_single_group_pipeline(group_id: str) -> PipelineStages:
    """Build aggregation pipeline to get a single group by id."""
    pipeline: PipelineStages = [
        {"$match": {"core.group_id": group_id}},
        group_project_stage(include_presets=True),
    ]
    return pipeline
