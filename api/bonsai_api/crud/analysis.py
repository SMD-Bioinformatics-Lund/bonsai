"""Functions for manipulating analysis result and associating it with a sample."""

from fastapi import UploadFile

from bonsai_api.utils import get_timestamp
from bonsai_api.db import Database
from bonsai_api.analysis_parsers.registry import get_parser
from .errors import EntryNotFound, UpdateDocumentError

async def add_analysis_to_sample(db: Database, sample_id: str, software: str, version: str, file: UploadFile):
    """Add a analysis to an exisitng sample."""
    # read file content
    content = await file.read()
    decoded = content.decode("utf-8")
    # parse the raw data
    parser = get_parser(software, version)
    data = parser(decoded)

    # update database
    update_obj = db.sample_collection.update_one(
        {"sample_id": sample_id}, 
        {"$set": {data.target_field: data.data.model_dump(mode="json"), "modified_at": get_timestamp()}}
    )

    if not update_obj.matched_count == 1:
        raise EntryNotFound(sample_id)
    if not update_obj.modified_count == 1:
        raise UpdateDocumentError(sample_id)