"""Serialize metadata/file/index workflows on the shared signature volume."""

from contextlib import contextmanager
from pathlib import Path
from threading import RLock

import fasteners

_THREAD_LOCK = RLock()


@contextmanager
def signature_workflow_lock(signature_dir: Path):
    """Use a separate lock from index-store locks; always acquire this first.

    The thread lock complements the process lock, whose OS locks do not exclude
    threads in the same process. Every worker must share the signature volume.
    """
    with _THREAD_LOCK:
        signature_dir.mkdir(parents=True, exist_ok=True)
        with fasteners.InterProcessLock(str(signature_dir / ".signature-workflow.lock")):
            yield
