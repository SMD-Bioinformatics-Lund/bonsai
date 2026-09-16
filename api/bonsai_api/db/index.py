"""Functions for creating and maintaining indexes."""

from typing import Any, Dict

from pymongo import ASCENDING, GEOSPHERE

# Create indexes for collections
IndexDefinition = Dict[str, Any]
SAMPLE_RUN_LIMS_INDEX: IndexDefinition = {
    "definition": [
        ("lims_id", ASCENDING),
        ("sequencing.sequencing_run_id", ASCENDING),
    ],
    "required": True,
    "options": {
        "name": "sample_lims_id_sequencing_run_id_unique",
        "unique": True,
        "partialFilterExpression": {
            "lims_id": {"$type": "string", "$gt": ""},
            "sequencing.sequencing_run_id": {"$type": "string", "$gt": ""},
        },
    },
}

INDEXES: dict[str, list[IndexDefinition]] = {
    "sample_group": [
        {
            "definition": [("core.group_id", ASCENDING)],
            "options": {
                "name": "sample_group",
                "background": True,
                "unique": True,
            },
        },
    ],
    "sample": [
        SAMPLE_RUN_LIMS_INDEX,
        {
            "definition": [("sample_id", ASCENDING), ("created_at", ASCENDING)],
            "options": {
                "name": "sample_sample_id",
                "background": True,
                "unique": True,
            },
        },
        {
            "definition": [("add_phenotype_prediction.type", ASCENDING)],
            "options": {
                "name": "sample_add_phenotype_prediction",
                "background": True,
                "unique": False,
            },
        },
    ],
    "location": [
        {
            "definition": [("location", GEOSPHERE)],
            "options": {
                "name": "location_2dsphere",
                "background": True,
                "unique": False,
            },
        },
    ],
    "user": [
        {
            "definition": [("username", ASCENDING)],
            "options": {
                "name": "user_username",
                "background": True,
                "unique": True,
            },
        },
    ],
    "analysis": [
        {
            "definition": [
                ("sample_id", ASCENDING),
                ("software", ASCENDING),
                ("software_version", ASCENDING),
                ("pipeline_run_id", ASCENDING)
            ],
            "options": {
                "name": "analysis_sample_id",
                "background": True,
                "unique": False,
            },
        },
    ],
    "curations": [
        {
            "definition": [
                ("analysis_id", ASCENDING),
                ("annotation_type", ASCENDING),
                ("target_index", ASCENDING),
            ],
            "options": {
                "name": "uniq_item_level_curation",
                "background": True,
                "unique": True,
                "partialFilterExpression": {"target_index": {"$exists": True}}
            },
        },
        {
            "definition": [
                ("analysis_id", ASCENDING),
                ("annotation_type", ASCENDING),
            ],
            "options": {
                "name": "uniq_analysis_level_curation",
                "background": True,
                "unique": True,
                "partialFilterExpression": {"target_index": {"$exists": True}}
            },
        }
    ]
}
