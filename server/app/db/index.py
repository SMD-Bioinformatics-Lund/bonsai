"""Functions for creating and maintaining indexes."""
from pymongo import ASCENDING, DESCENDING, TEXT, IndexModel

# Create indexes for collections
INDEXES = {
    "sample_group": {
        "definition": [("collectionId", ASCENDING)],
        "options": {
            "name": "sample_group",
            "background": True,
            "unique": True,
        },
    },
    "sample": {
        "definition": [("sample_id", ASCENDING), ("in_collections", ASCENDING)],
        "options": {
            "name": "sample_sample_id",
            "background": True,
            "unique": True,
        }
    }
}
