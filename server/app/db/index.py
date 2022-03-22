"""Functions for creating and maintaining indexes."""
from pymongo import ASCENDING, DESCENDING, TEXT, GEOSPHERE  

# Create indexes for collections
INDEXES = {
    "sample_group": [
        {
            "definition": [("groupId", ASCENDING)],
            "options": {
                "name": "sample_group",
                "background": True,
                "unique": True,
            },
        },
    ],
    "sample": [
        {
            "definition": [("sample_id", ASCENDING)],
            "options": {
                "name": "sample_sample_id",
                "background": True,
                "unique": True,
            },
        },
    ],
    "phenotype": [
        {
            "definition": [("addPhenotypePrediction.type", ASCENDING)],
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
    ]
}
