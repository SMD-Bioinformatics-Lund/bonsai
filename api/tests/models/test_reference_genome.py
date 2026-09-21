"""Samples and tracks name their reference genome by accession or internal id."""

import pytest

from bonsai_api.models.genomic_resource import GenomicResourceCreate
from bonsai_api.models.reference_genome import AddReferenceGenomeRequest


@pytest.mark.parametrize("key", ["reference_genome_accession", "reference_genome_id"])
def test_add_reference_genome_accepts_accession_or_id(key):
    assert AddReferenceGenomeRequest.model_validate({key: "GCF_000012045.1"}).reference_genome_id == "GCF_000012045.1"


@pytest.mark.parametrize("key", ["reference_genome_accession", "reference_genome_id"])
def test_genomic_resource_accepts_accession_or_id(key):
    body = {key: "GCF_000012045.1", "pipeline_run_id": "run1", "resource_data": []}
    assert GenomicResourceCreate.model_validate(body).reference_genome_id == "GCF_000012045.1"
