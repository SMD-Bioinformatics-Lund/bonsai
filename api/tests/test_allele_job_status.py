"""Unplaced-sample accounting survives queue polling."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from bonsai_api.redis import queue


def test_job_status_includes_unplaced_samples_without_changing_newick_result(
    monkeypatch,
):
    unplaced = [
        {
            "sample_id": "empty",
            "label": "LAB-EMPTY",
            "reason": "No usable allele calls are available.",
        }
    ]
    job = SimpleNamespace(
        exc_info=None,
        get_status=lambda **_: "finished",
        origin="allele_cluster",
        func_name="allele_cluster_service.tasks.cluster",
        return_value=lambda: "(a:1,b:0);",
        enqueued_at=datetime.now(timezone.utc),
        started_at=None,
        ended_at=None,
        meta={"unplaced_samples": unplaced},
    )
    monkeypatch.setattr(queue, "Job", SimpleNamespace(fetch=Mock(return_value=job)))
    result = queue.check_redis_job_status("job")
    assert result.result == "(a:1,b:0);"
    assert result.model_dump()["unplaced_samples"] == unplaced
