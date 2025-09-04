"""Entry point for starting jobs at the service."""

from typing import Any, Callable

from rq import Queue, SimpleWorker
from rq.job import Job

from .handlers import (
    add_signature,
    add_to_index,
    check_signature,
    cleanup_removed_files,
    cluster_samples,
    exclude_from_analysis,
    find_similar_and_cluster,
    get_data_integrity_report,
    remove_from_index,
    remove_signature,
    run_data_integrity_check,
    search_similar,
)

REGISTRY: dict[str, Callable[..., Any]] = {
    "add_signature": add_signature,
    "remove_signature": remove_signature,
    "add_to_index": add_to_index,
    "remove_from_index": remove_from_index,
    "exclude_from_analysis": exclude_from_analysis,
    "search_similar": search_similar,
    "cluster_samples": cluster_samples,
    "find_similar_and_cluster": find_similar_and_cluster,
    "check_signature": check_signature,
    "check_data_integrity": run_data_integrity_check,
    "get_integrity_report": get_data_integrity_report,
    "cleanup_removed_files": cleanup_removed_files,
}

ALLOWED_ENTRYPOINTS: set[str] = {
    "minhash_service.tasks.dispatch_job",
    "minhash_service.tasks.dispatch.dispatch_job",
}


def dispatch_job(*, task: str, **kwargs: Any):
    """Execute a task."""
    if task not in REGISTRY:
        raise ValueError(f"Unknown task: {task}.")

    func = REGISTRY[task]
    return func(**kwargs)


class SimpleWhitelistWorker(SimpleWorker):
    """A SimpleWorker that whitelist only the dispatch function."""

    def execute_job(self, job: Job, queue: Queue):
        """Execute only allowed jobs."""
        if job.func_name not in ALLOWED_ENTRYPOINTS:
            raise ValueError(f"Rejected job: {job.func_name}")
        return super().execute_job(job, queue)
