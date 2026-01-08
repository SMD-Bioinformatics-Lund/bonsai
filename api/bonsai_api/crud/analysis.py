"""CRUD helpers for analysis records."""

import logging
from datetime import datetime
from typing import Any

from bonsai_api.db import Database
from bonsai_api.utils import get_timestamp

LOG = logging.getLogger(__name__)


async def create_analysis(db: Database, *, doc: dict[str, Any]) -> str:
    """Insert an analysis record and return its id."""
    doc_copy = dict(doc)
    doc_copy.setdefault("created_at", get_timestamp())

    res = await db.analysis_collection.insert_one(doc_copy)
    LOG.info("Inserted analysis record %s for sample %s", res.inserted_id, doc.get("sample_id"))
    return str(res.inserted_id)


async def get_analysis(db: Database, *, analysis_id: str) -> dict[str, Any] | None:
    doc = await db.analysis_collection.find_one({"_id": analysis_id})
    return doc
