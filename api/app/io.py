"""IO operations."""

from collections import defaultdict
from typing import List

import pandas as pd
from prp.models.phenotype import GeneBase, PredictionSoftware, VariantBase
from pydantic import BaseModel

from .models.sample import SampleInDatabase


def _sort_motifs_on_phenotype(prediction: List[GeneBase | VariantBase]):
    """Sort resistance genes and variants by the antibiotics they yeid resistance to."""
    result = defaultdict(list)
    for motif in prediction:
        if len(motif.phenotypes) == 0:
            result["none"].append(motif)
        else:
            # add variant to all phenotypes
            for phenotype in motif.phenotypes:
                # make a copy with only one phenotypes
                upd_motif = motif.copy(update={"phenotypes": [phenotype]})
                result[phenotype.name].append(upd_motif)
    return result


def _fmt_variant(variant):
    """"""
    WHO_CLASSES = {
        "Assoc w R": 1,
        "Assoc w R - Interim": 2,
        "Uncertain significance": 3,
        "Not assoc w R - Interim": 4,
        "Not assoc w R": 5,
    }
    var_type = variant.variant_type[:3]
    variant_desc = f"{variant.gene_symbol}_{variant.position}_{var_type}"
    # annotate variant frequency for minority variants
    if variant.frequency < 1:
        variant_desc = f"{variant_desc}({variant.frequency * 100:.1f}%)"
    # annotate WHO classification
    who_group = WHO_CLASSES.get(variant.phenotypes[0].note)
    if who_group is not None:
        variant_desc = f"{variant_desc} WHO-{who_group}"
    return variant_desc


def _fmt_mtuberculosis(sample: SampleInDatabase):
    """Format M. tuberculosis result.

    - one row per antibiotic with all variants

    :param sample: Prediction results
    :type sample: SampleInDatabase
    """
    TARGETED_ANTIBIOTICS = {
        "rifampicin": "rif",
        "isoniazid": "inh",
        "pyrazinamide": "pza",
        "ethambutol": "etm",
        "amikacin": "ami",
        "levofloxacin": "lev",
    }
    for pred_res in sample.element_type_result:
        # only include TBprofiler result
        if not pred_res.software == PredictionSoftware.TBPROFILER.value:
            continue

        # reformat predicted resistance
        sorted_variants = _sort_motifs_on_phenotype(pred_res.result.variants)

        # create tabular result
        result = []
        for antibiotic in TARGETED_ANTIBIOTICS:
            # concat variants
            if antibiotic in sorted_variants:
                call = "Mutation påvisad"
                variants = ";".join(
                    _fmt_variant(var) for var in sorted_variants[antibiotic]
                )
            else:
                # add non-called resistance
                call = "Mutation ej påvisad"
                variants = "-"
            # add result
            result.append(
                {
                    "parameter": f"{TARGETED_ANTIBIOTICS[antibiotic].upper()} NGS",
                    "result": call,
                    "variants": variants,
                }
            )
    return pd.DataFrame(result)


def sample_to_kmlims(sample: SampleInDatabase) -> pd.DataFrame:
    """Convert sample information to KMLIMS format."""
    match sample.run_metadata.run.analysis_profile:
        case "mycobacterium_tuberculosis":
            pred_res = _fmt_mtuberculosis(sample)
        case default:
            raise NotImplementedError(
                f"No export function for {sample.run_metadata.run.analysis_profile}"
            )
    return pred_res
