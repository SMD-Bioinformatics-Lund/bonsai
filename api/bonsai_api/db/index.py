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
                "name": "sample_group_id",
                "background": True,
                "unique": True,
            },
        },
        {
            "definition": [("core.group_key", ASCENDING)],
            # Uploads reference groups by key, so uniqueness must not silently fail.
            "required": True,
            "options": {
                "name": "sample_group_key",
                "background": True,
                "unique": True,
                # Groups created before group keys existed have no core.group_key.
                "partialFilterExpression": {"core.group_key": {"$type": "string"}},
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
        {
            "definition": [("external_sample_id", ASCENDING)],
            "options": {
                "name": "sample_external_sample_id",
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
            "definition": [("id", ASCENDING)],
            "options": {
                "name": "reference_genome_id",
                "background": True,
                "unique": True,
            },
        },
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
                "partialFilterExpression": {
                    "sequence_accessions.0": {"$exists": True}
                },
            },
        },
    ],
    "curations": [
        {
            "definition": [
                ("analysis_id", ASCENDING),
                ("analysis_type", ASCENDING),
                ("annotation_type", ASCENDING),
                ("result_key", ASCENDING),
            ],
            "required": True,
            "options": {
                "name": "uniq_curation_result",
                "background": True,
                "unique": True,
            },
        }
    ]
}
