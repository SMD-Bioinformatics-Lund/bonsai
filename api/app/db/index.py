"""Functions for creating and maintaining indexes."""
from pymongo import ASCENDING, DESCENDING, GEOSPHERE, TEXT

# Create indexes for collections
INDEXES = {
    "sample_group": [
        {
            "definition": [("group_id", ASCENDING)],
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
    ],
    "location": [
        {
            "definition": [("_id", ASCENDING)],
            "options": {
                "name": "location_unique_id",
                "background": True,
                "unique": True,
            },
        },
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
}
