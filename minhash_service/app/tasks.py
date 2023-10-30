"""Define reddis tasks."""
from time import sleep
from typing import List
from pathlib import Path
from .minhash import (write_genome_signature_file, add_genome_signatures_to_index, get_signatures_similar_to_reference, SimilarSignatures)

import logging
LOG = logging.getLogger(__name__)


def add_signature(sample_id: str, signature) -> str:
    """
    Find signatures similar to reference signature.

    Retun list of similar signatures that describe signature and similarity.
    """
    signature_path = write_genome_signature_file(sample_id, signature)
    return str(signature_path)


def index(signature_files: List[Path]):
    """Index sourmash signatures."""
    LOG.info('Indexing signatures...')
    res = add_genome_signatures_to_index(signature_files)
    signatures = ", ".join([file.name for file in signature_files])
    if res:
        msg = f"Appended {signatures}"
    else:
        msg = f"Failed to append signatures, {signatures}"
    return msg


def similar(sample_id: str, min_similarity: float = 0.5, limit: int | None = None) -> SimilarSignatures:
    """
    Find signatures similar to reference signature.

    Retun list of similar signatures that describe signature and similarity.
    """
    samples = get_signatures_similar_to_reference(sample_id, min_similarity=min_similarity, limit=limit)
    LOG.info(f"Finding samples similar to {sample_id} with min similarity {min_similarity}; limit {limit}")
    results = [s.model_dump() for s in samples]
    return results


def cluster(signatures):
    """Cluster multiple sample on their sourmash signatures."""
    sleep(120)
    pass


def find_similar_and_cluster(ref_signature: Path, min_similarity: float = 0.5, limit: int | None = None) -> str:
    """Find similar samples and cluster them on their minhash profile."""
    samples = get_signatures_similar_to_reference(ref_signature, min_similarity=min_similarity, limit=limit)
    pass