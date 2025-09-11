"""Extract and format data for lims export."""

import logging
from typing import Literal
from bonsai_api.models.sample import SampleInDatabase
from typing import Literal, cast

from prp.models.species import BrackenSpeciesPrediction

LOG = logging.getLogger(__name__)


def get_mlst_typing(sample: SampleInDatabase) -> tuple[int | Literal['novel'], str]:
    """Extract and format MLST (Multi-Locus Sequence Typing) result from a sample."""
    for ty in sample.typing_result:
        if ty.type == 'mlst':
            mlst_st = ty.result.sequence_type or "novel"
            return mlst_st, ""
    raise ValueError(f"Sample '{sample.sample_id}' doesn't have MLST results.")


def get_species_prediction(sample: SampleInDatabase) -> tuple[str, str]:
    """Extract and format species prediction result using Bracken."""
    for pred in sample.species_prediction:
        if pred.software == 'bracken':
            spp_pred = cast(list[BrackenSpeciesPrediction], pred.result)  # improve type hinting
            # ensure that best hit is first
            if len(spp_pred) == 0:
                LOG.warning("Sample %s did not have any bracken predicitons", sample.sample_id)
                return "", ""
            top_hit: BrackenSpeciesPrediction = sorted(spp_pred, key=lambda s: s.fraction_total_reads, reverse=True)[0]
            return top_hit.scientific_name, ""
    raise ValueError(f"Sample '{sample.sample_id}' dont have bracken species prediction result.")
