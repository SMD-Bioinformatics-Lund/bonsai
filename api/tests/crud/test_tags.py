"""Test crud functions that creates tags."""

from pydantic import BaseModel
from prp.models.species import SppMethodIndex, BrackenSpeciesPrediction, MykrobeSpeciesPrediction, SppPredictionSoftware


from bonsai_api.crud.tags import evaluate_bracken, evaluate_mykrobe, SPP_EVALUATORS, flag_uncertain_spp_prediction
from bonsai_api.models.tags import Tag


class SampleInDatabase(BaseModel):
    species_prediction: list[SppMethodIndex] = []


def test_add_contamination_tag_when_failed():
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
    bracken_spp = BrackenSpeciesPrediction(
        scientificName='Staphylococcus aureus', taxId=None, taxLevel='species',
        krakenAssignedReads=100000, addedReads=10000, fractionTotalReads=0.95)
    mykrobe_spp = MykrobeSpeciesPrediction(
        scientificName='Mycobacterium tuberculosis', taxId=None, phylogenetic_group="Mycobacterium",
        phylogenetic_group_coverage=0.99, species_coverage=0.99)
    spp = [
        SppMethodIndex(software=SppPredictionSoftware.BRACKEN, result=[bracken_spp]),
        SppMethodIndex(software=SppPredictionSoftware.MYKROBE, result=[mykrobe_spp]),
    ]
    sample = SampleInDatabase(species_prediction=list(spp))

    tags: list[Tag] = []
    flag_uncertain_spp_prediction(tags, sample)

    assert tags == []


def 