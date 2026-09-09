"""Functions for creating and maintaining indexes."""

from typing import Any, Dict

from pymongo import ASCENDING, GEOSPHERE

# Create indexes for collections
IndexDefinition = Dict[str, Any]
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
        {
            "definition": [("external_sample_id", ASCENDING)],
            "options": {
                "name": "sample_external_sample_id",
                "background": True,
                # Not unique: existing data may already contain duplicate
                # external_sample_id values, so this can't be enforced yet.
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
                ("subcommand", ASCENDING),
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
    "reference_genome": [
        {
            "definition": [("accession", ASCENDING)],
            "options": {
                "name": "reference_genome_accession",
                "background": True,
                "unique": True,
            },
        },
        {
            "definition": [("sequence_accessions", ASCENDING)],
            "options": {
                "name": "reference_genome_sequence_accessions",
                "background": True,
                "unique": True,
                # Multikey unique index: a sequence accession may only belong to
                # one reference genome. Partial filter keeps documents with no
                # sequence accessions from colliding on the empty-array key.
                "partialFilterExpression": {"sequence_accessions.0": {"$exists": True}},
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
