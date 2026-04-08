"""CRUD helpers for analysis records."""

import logging
from typing import Any

from bonsai_api.db import Database
from bonsai_api.utils import get_timestamp
from pymongo.client_session import ClientSession

LOG = logging.getLogger(__name__)


async def create_analysis(
    db: Database, *, doc: dict[str, Any], session: ClientSession | None = None
) -> str:
    """Insert an analysis record and return its id."""
    doc_copy = dict(doc)
    doc_copy.setdefault("created_at", get_timestamp())

    res = await db.analysis_collection.insert_one(doc_copy, session=session)
    LOG.info(
        "Inserted analysis record %s for sample %s",
        res.inserted_id,
        doc.get("sample_id"),
    )
    return str(res.inserted_id)


async def get_analysis(db: Database, *, analysis_id: str, session: ClientSession | None = None) -> dict[str, Any] | None:
    """Retrieve an analysis record by its id.o"""

    doc = await db.analysis_collection.find_one({"id": analysis_id}, session=session)
    return doc


async def analysis_exists(
    db: Database,
    *,
    sample_id: str,
    software: str,
    software_version: str,
    pipeline_run: str,
    session: ClientSession | None = None
) -> bool:
    """Check if an analysis record exists from sample id, software, software version, and pipeline run."""
    doc = await db.analysis_collection.find_one(
        {
            "sample_id": sample_id,
            "software": software,
            "software_version": software_version,
            "pipeline_run_id": pipeline_run,
        },
        {"_id": 1},
        session=session,
    )
    return bool(doc)
