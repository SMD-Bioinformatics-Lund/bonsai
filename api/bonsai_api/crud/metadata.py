"""Metadata related CRUD operations."""

from typing import Any
from pydantic import TypeAdapter
from pymongo.results import UpdateResult

from bonsai_api.models.group import OverviewTableColumn
from bonsai_api.db import Database
from bonsai_api.models.metadata import InputMetaEntry, MetaEntriesInDb, MetaEntryInDb
from bonsai_api.io import parse_metadata_table

from .sample import get_sample
from .errors import EntryNotFound


async def add_metadata_to_sample(
    sample_id: str, metadata: list[InputMetaEntry], db: Database
) -> bool:
    """Add one or more metadata records to a sample in the database."""

    # 1. verify that fieldname does not already exist
    sample_obj = await get_sample(sample_id=sample_id, db=db)
    input_fieldnames = {met.fieldname for met in metadata}
    db_fieldnames = {meta.fieldname for meta in sample_obj.metadata}
    if len(input_fieldnames & db_fieldnames) > 0:
        raise ValueError(
            f"Metadata field '{metadata.fieldname}' already exist for sample {sample_id}"
        )

    # 2. push new metadata entry to existing metadata
    meta_info: list[MetaEntryInDb] = []
    for meta in sample_obj.metadata:
        if meta.fieldname not in input_fieldnames:
            meta_info.append(meta)
    # if entry is a table, serialize and reformat
    for record in metadata:
        if record.type == "table":
            meta_info.append(parse_metadata_table(entry=record))
        else:
            meta_info.append(record)

    cursor: UpdateResult = await db.sample_collection.update_one(
        {"sample_id": sample_id},
        {"$set": {"metadata": [meta.model_dump() for meta in meta_info]}},
    )
    if cursor.matched_count == 0:
        raise EntryNotFound(sample_id)
    is_updated = cursor.matched_count == 1 and cursor.modified_count == 1
    if not is_updated:
        raise ValueError("Metadata not modified.")
    return True


async def get_metadata_fields_for_samples(
    db: Database, sample_ids: list[str] | None = None
) -> Any:
    """Get uniqe metadata fieldnames and types for a collection of samples."""
    query: dict[str, Any] = {}
    if sample_ids is not None and len(sample_ids) > 0:
        query = {"sample_id": {"$in": sample_ids}}

    # get unique metadata fieldnames
    result = await db.sample_collection.distinct(key="metadata", query=query)
    meta_obj = TypeAdapter(MetaEntriesInDb).validate_python(result)
    uniq_obj: dict[str, MetaEntryInDb] = {}
    for meta in meta_obj:
        if meta.fieldname not in uniq_obj:
            uniq_obj[meta.fieldname] = meta

    cols = [
        OverviewTableColumn(
            id=entry.fieldname.lower().replace(" ", "-"),
            label=entry.fieldname,
            path=f'$.metadata[*][?(@.fieldname = "{entry.fieldname}")].value',
            type=entry.type
        )
        for entry in uniq_obj.values()
    ]
    return cols
