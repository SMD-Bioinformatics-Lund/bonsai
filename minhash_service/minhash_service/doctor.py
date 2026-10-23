"""Availability and search-index checks for the API's doctor command."""

import os
from collections import defaultdict

from .core.config import cnf
from .core.factories import create_signature_repo
from .signatures.index import create_index_store


def check_samples(samples: list[dict]) -> dict:
    """Read metadata and the index once; preserve shared-checksum eligibility."""
    records = list(create_signature_repo().get_all_signatures())
    by_sample = defaultdict(list)
    eligible_checksums = set()
    failed_ids = {sample["sample_id"] for sample in samples if sample["qc_failed"]}
    for record in records:
        if record.kmer_size != cnf.kmer_size:
            continue
        by_sample[record.sample_id].append(record)
        if (
            not record.exclude_from_analysis
            and not record.marked_for_deletion
            and record.sample_id not in failed_ids
        ):
            eligible_checksums.add(record.signature_checksum)

    findings = []
    errors = []
    indexed = None
    index_path = (
        cnf.signature_dir
        / "indexes"
        / f"genomes_{cnf.index_format.value.lower()}_index"
    )
    if any(by_sample[s["sample_id"]] for s in samples):
        try:
            if not index_path.exists():
                indexed = set()
            else:
                index = create_index_store(index_path, cnf.index_format)
                indexed = index.list_signature_checksums()
        except Exception as error:
            errors.append(f"MinHash search index could not be checked: {error}")

    def add(sample_id, file_type, message, path=None):
        findings.append(
            {
                "sample_id": sample_id,
                "file_type": file_type,
                "message": message,
                "path": str(path) if path else None,
            }
        )

    for sample in samples:
        sid = sample["sample_id"]
        matching = by_sample[sid]
        if not matching:
            add(sid, "minhash", f"No signature metadata for k-mer size {cnf.kmer_size}")
            continue
        if len(matching) > 1:
            add(
                sid,
                "minhash",
                "Multiple signature records for the configured k-mer size",
            )
        for record in matching:
            path = record.signature_path
            try:
                if not path.is_file():
                    add(sid, "minhash", "Signature file is missing", path)
                elif not os.access(path, os.R_OK):
                    add(sid, "minhash", "Signature file is unreadable", path)
                elif path.stat().st_size == 0:
                    add(sid, "minhash", "Signature file is empty", path)
            except OSError as error:
                add(sid, "minhash", f"Cannot access signature: {error}", path)

            if record.marked_for_deletion:
                add(sid, "minhash", "Signature is marked for deletion", path)
            if sample["qc_failed"]:
                if not record.exclude_from_analysis:
                    add(
                        sid,
                        "minhash-index",
                        "QC-failed signature is not excluded from analysis",
                    )
                # An excluded signature may share an index entry with another sample.
                if record.has_been_indexed or (
                    indexed is not None
                    and record.signature_checksum in indexed
                    and record.signature_checksum not in eligible_checksums
                ):
                    add(sid, "minhash-index", "QC-failed signature remains indexed")
            else:
                if record.exclude_from_analysis:
                    add(
                        sid,
                        "minhash-index",
                        "Signature is unexpectedly excluded from analysis",
                    )
                if not record.has_been_indexed:
                    add(
                        sid,
                        "minhash-index",
                        "Signature metadata is not marked as indexed",
                    )
                if indexed is not None and record.signature_checksum not in indexed:
                    add(
                        sid,
                        "minhash-index",
                        "Signature is missing from the search index",
                    )
    return {"findings": findings, "errors": errors}
