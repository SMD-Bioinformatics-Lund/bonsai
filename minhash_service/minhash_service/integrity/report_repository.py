from typing import Any
from pymongo import DESCENDING
from pymongo.collection import Collection

from .report_model import IntegrityReport

class IntegrityReportRepository:
    """
    Repository for integrity reports.

    Pass in a ready Collection (with auth, TLS, timeouts, etc. configured).
    """

    def __init__(self, collection: Collection[Any]):
        self._col = collection
    
    def save(self, report: IntegrityReport) -> None:
        """Save a report to the database."""
        self._col.insert_one(report.model_dump())
    
    def get_latest(self) -> IntegrityReport | None:
        """Retrieve the latest integrity report from the database."""
        doc = self._col.find_one(sort=[("timestamp", DESCENDING)])
        if doc:
            return IntegrityReport.model_validate(doc)
        return None
