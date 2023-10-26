"""Define reddis tasks."""
from time import sleep
from typing import List
from pathlib import Path
import logging
LOG = logging.getLogger(__name__)

def index(sample_ids: List[Path]):
    """Index sourmash signatures."""
    LOG.info('Indexing signatures...')
    sleep(120)
    return f"finished indexing {len(sample_ids)}"


def cluster(*args, **kwargs):
    """Cluster sourmash signatures."""
    LOG.info([args, kwargs])
    sleep(120)
    pass