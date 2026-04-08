"""Test crud functions that creates tags."""

import pytest
from bonsai_api.crud.tags import flag_uncertain_spp_prediction
from bonsai_api.models.tags import Tag
from bonsai_api.models.sample import AnalysisViewEntryDb
from prp.models.enums import AnalysisSoftware
from prp.parse.models.bracken import BrackenSpeciesPrediction
from prp.parse.models.mykrobe import MykrobeSpeciesPrediction
from pydantic import BaseModel


class SampleInDatabase(BaseModel):
    """Mocked sample model."""

    species_prediction: list[AnalysisViewEntryDb] = []


def test_add_contamination_tag_when_failed():
    """Test that faild checks adds contamination tags."""
    bracken_spp = BrackenSpeciesPrediction(
        scientific_name="Staphylococcus aureus",
        taxonomy_id=None,
        taxonomy_lvl="species",
        kraken_assigned_reads=100000,
        added_reads=10000,
        fraction_total_reads=0.4,
    )
    mykrobe_spp = MykrobeSpeciesPrediction(
        scientific_name="Mycobacterium tuberculosis",
        phylogenetic_group="Mycobacterium",
        phylogenetic_group_coverage=0.5,
        species_coverage=0.8,
    )
    spp = [
        AnalysisViewEntryDb(
            software=AnalysisSoftware.BRACKEN,
            software_version="0.1.0",
            analysis_type="species_prediction",
            analysis_id="analysis1",
            status="parsed",
            result=[bracken_spp]),
        AnalysisViewEntryDb(
            software=AnalysisSoftware.MYKROBE,
            software_version="0.1.0",
            analysis_type="species_prediction",
            analysis_id="analysis1",
            status="parsed",
            result=[mykrobe_spp]),
    ]
    sample = SampleInDatabase(species_prediction=list(spp))

    tags: list[Tag] = []
    flag_uncertain_spp_prediction(tags, sample)

    assert len(tags) == 2
    assert "fraction_total_reads" in tags[0].description
    assert "species_coverage" in tags[1].description


def test_no_tags_when_all_contamination_checks_pass():
    """Passed contamination checks dont add tags."""
    bracken_spp = BrackenSpeciesPrediction(
        scientific_name="Staphylococcus aureus",
        taxonomy_id=None,
        taxonomy_lvl="species",
        kraken_assigned_reads=100000,
        added_reads=10000,
        fraction_total_reads=0.9,
    )
    mykrobe_spp = MykrobeSpeciesPrediction(
        scientific_name="Mycobacterium tuberculosis",
        phylogenetic_group="Mycobacterium",
        phylogenetic_group_coverage=99,
        species_coverage=98,
    )
    spp = [
        AnalysisViewEntryDb(
            software=AnalysisSoftware.BRACKEN,
            software_version="0.1.0",
            analysis_type="species_prediction",
            analysis_id="analysis1",
            status="parsed",
            result=[bracken_spp]),
        AnalysisViewEntryDb(
            software=AnalysisSoftware.MYKROBE,
            software_version="0.1.0",
            analysis_type="species_prediction",
            analysis_id="analysis1",
            status="parsed",
            result=[mykrobe_spp]),
    ]
    sample = SampleInDatabase(species_prediction=list(spp))

    tags: list[Tag] = []
    flag_uncertain_spp_prediction(tags, sample)

    assert not tags


def test_unknown_software_raises_exeption():
    """Test that providing a unknown software raises an error."""
    mykrobe_spp = MykrobeSpeciesPrediction(
        scientific_name="Mycobacterium tuberculosis",
        phylogenetic_group="Mycobacterium",
        phylogenetic_group_coverage=0.5,
        species_coverage=0.8,
    )
    with pytest.raises(NotImplementedError):
        spp = [
            AnalysisViewEntryDb(
                software=AnalysisSoftware.TBPROFILER,
                software_version="0.1.0",
                analysis_type="species_prediction",
                analysis_id="analysis1",
                status="parsed",
                result=[mykrobe_spp]),
        ]
        sample = SampleInDatabase(species_prediction=list(spp))

        tags: list[Tag] = []
        flag_uncertain_spp_prediction(tags, sample)
