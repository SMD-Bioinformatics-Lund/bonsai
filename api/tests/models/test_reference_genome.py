"""Samples and tracks name their reference genome by accession or internal id."""

import pytest
from pydantic import ValidationError

from bonsai_api.models.genomic_resource import GenomicResourceCreate
from bonsai_api.models.reference_genome import AddReferenceGenomeRequest


@pytest.mark.parametrize("key", ["reference_genome_accession", "reference_genome_id"])
def test_add_reference_genome_accepts_accession_or_id(key):
    assert AddReferenceGenomeRequest.model_validate({key: "GCF_000012045.1"}).reference_genome_id == "GCF_000012045.1"


@pytest.mark.parametrize("key", ["reference_genome_accession", "reference_genome_id"])
def test_genomic_resource_accepts_accession_or_id(key):
    body = {key: "GCF_000012045.1", "pipeline_run_id": "run1", "resource_data": []}
    assert GenomicResourceCreate.model_validate(body).reference_genome_id == "GCF_000012045.1"


@pytest.mark.parametrize(
    "model", [AddReferenceGenomeRequest, GenomicResourceCreate]
)
def test_an_identifier_is_required(model):
    with pytest.raises(ValidationError):
        model.model_validate({"pipeline_run_id": "run1", "resource_data": []})


def test_the_accession_wins_when_both_keys_are_given():
    """AliasChoices resolves left to right, so the accession takes precedence."""
    body = {
        "reference_genome_accession": "GCF_000012045.1",
        "reference_genome_id": "01a0c39b-9440-7ce2-8188-08d85f0c5ecb",
    }
    assert AddReferenceGenomeRequest.model_validate(body).reference_genome_id == "GCF_000012045.1"
