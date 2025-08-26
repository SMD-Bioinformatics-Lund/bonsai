"""Test crud functions that creates tags."""

from pydantic import BaseModel
from prp.models.species import SppMethodIndex, BrackenSpeciesPrediction, MykrobeSpeciesPrediction, SppPredictionSoftware
import pytest


from bonsai_api.crud.tags import flag_uncertain_spp_prediction
from bonsai_api.models.tags import Tag


class SampleInDatabase(BaseModel):
    """Mocked sample model."""
    species_prediction: list[SppMethodIndex] = []


def test_add_contamination_tag_when_failed():
    """Test that faild checks adds contamination tags."""
    bracken_spp = BrackenSpeciesPrediction(
        scientificName='Staphylococcus aureus', taxId=None, taxLevel='species',
        krakenAssignedReads=100000, addedReads=10000, fractionTotalReads=0.4)
    mykrobe_spp = MykrobeSpeciesPrediction(
        scientificName='Mycobacterium tuberculosis', taxId=None, phylogenetic_group="Mycobacterium",
        phylogenetic_group_coverage=0.5, species_coverage=0.8)
    spp = [
        SppMethodIndex(software=SppPredictionSoftware.BRACKEN, result=[bracken_spp]),
        SppMethodIndex(software=SppPredictionSoftware.MYKROBE, result=[mykrobe_spp]),
    ]
    sample = SampleInDatabase(species_prediction=list(spp))

    tags: list[Tag] = []
    flag_uncertain_spp_prediction(tags, sample)

    assert len(tags) == 2
    assert 'fraction_total_reads' in tags[0].description
    assert 'species_coverage' in tags[1].description


def test_no_tags_when_all_contamination_checks_pass():
    """Passed contamination checks dont add tags."""
    bracken_spp = BrackenSpeciesPrediction(
        scientificName='Staphylococcus aureus', taxId=None, taxLevel='species',
        krakenAssignedReads=100000, addedReads=10000, fractionTotalReads=0.95)
    mykrobe_spp = MykrobeSpeciesPrediction(
        scientificName='Mycobacterium tuberculosis', taxId=None, phylogenetic_group="Mycobacterium",
        phylogenetic_group_coverage=99, species_coverage=99)
    spp = [
        SppMethodIndex(software=SppPredictionSoftware.BRACKEN, result=[bracken_spp]),
        SppMethodIndex(software=SppPredictionSoftware.MYKROBE, result=[mykrobe_spp]),
    ]
    sample = SampleInDatabase(species_prediction=list(spp))

    tags: list[Tag] = []
    flag_uncertain_spp_prediction(tags, sample)

    assert not tags


def test_unknown_software_raises_exeption():
    """Test that providing a unknown software raises an error."""
    mykrobe_spp = MykrobeSpeciesPrediction(
        scientificName='Mycobacterium tuberculosis', taxId=None, phylogenetic_group="Mycobacterium",
        phylogenetic_group_coverage=99, species_coverage=99)
    spp = [
        SppMethodIndex(software=SppPredictionSoftware.TBPROFILER, result=[mykrobe_spp]),
    ]
    sample = SampleInDatabase(species_prediction=list(spp))

    tags: list[Tag] = []
    with pytest.raises(NotImplementedError):
        flag_uncertain_spp_prediction(tags, sample)
