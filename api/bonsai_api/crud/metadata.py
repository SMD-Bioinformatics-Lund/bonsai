"""Metadata related CRUD operations."""

from typing import Any

from bonsai_api.db import Database
from bonsai_api.exceptions import EntryNotFound
from bonsai_api.io import parse_metadata_table

# from bonsai_api.models.group import SampleTableColumnInput
from bonsai_api.models.metadata import InputMetaEntry, MetaEntriesInDb, MetaEntryInDb
from pydantic import TypeAdapter
from pymongo.results import UpdateResult

from .sample import get_sample_by_id


async def add_metadata_to_sample(
    sample_id: str, metadata: list[InputMetaEntry], db: Database
) -> bool:
    """Add one or more metadata records to a sample in the database."""

    # 1. verify that fieldname does not already exist
    sample_obj = await get_sample_by_id(db, sample_id=sample_id)
    input_fieldnames = {met.fieldname for met in metadata}
    sample_meta = sample_obj['metadata']
    db_fieldnames = {meta["fieldname"] for meta in sample_meta}
    if len(input_fieldnames & db_fieldnames) > 0:
        raise FileExistsError(
            f"Metadata field '{input_fieldnames}' already exist for sample {sample_id}"
        )

    # 2. push new metadata entry to existing metadata
    meta_info: list[dict[str, Any]] = []
    # if entry is a table, serialize and reformat
    for record in metadata:
        if record.type == "table":
            meta_info.append(parse_metadata_table(entry=record).model_dump())
        else:
            meta_info.append(record.model_dump())

    cursor: UpdateResult = await db.sample_collection.update_one(
        {"sample_id": sample_id, "metadata.fieldname": {"$nin": list(input_fieldnames)}},
        {"$push": {"metadata": {"$each": meta_info}}},
    )
    if cursor.matched_count == 0:
        if await get_sample_by_id(db, sample_id=sample_id) is None:
            raise EntryNotFound(sample_id)
        raise FileExistsError("A metadata field was added by another request")
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

    # cols = [
    #     SampleTableColumnInput(
    #         id=entry.fieldname.lower().replace(" ", "-"),
    #         label=entry.fieldname,
    #         path=f'$.metadata[*][?(@.fieldname = "{entry.fieldname}")].value',
    #         type=entry.type,
    #     )
    #     for entry in uniq_obj.values()
    # ]
    cols = []
    return cols
