"""Parse Mykrobe results."""

import logging
import re
from pathlib import Path
from typing import Any, Dict, Union

import numpy as np
import pandas as pd

from prp.models.species import (
    MykrobeSpeciesPrediction,
    SppMethodIndex,
    SppPredictionSoftware,
)

from ..models.metadata import SoupType, SoupVersion
from ..models.phenotype import (
    AMRMethodIndex,
    AnnotationType,
    ElementType,
    ElementTypeResult,
    MykrobeVariant,
    PhenotypeInfo,
)
from ..models.phenotype import PredictionSoftware as Software
from ..models.phenotype import VariantSubType, VariantType
from ..models.sample import MethodIndex
from ..models.typing import ResultLineageBase, TypingMethod
from .utils import get_nt_change, is_prediction_result_empty

LOG = logging.getLogger(__name__)


def _get_mykrobe_amr_sr_profie(mykrobe_result):
    """Get mykrobe susceptibility/resistance profile."""
    susceptible = set()
    resistant = set()

    if not mykrobe_result:
        return {}

    for element_type in mykrobe_result:
        if element_type["susceptibility"].upper() == "R":
            resistant.add(element_type["drug"])
        elif element_type["susceptibility"].upper() == "S":
            susceptible.add(element_type["drug"])
        else:
            # skip rows if no resistance predictions were identified
            continue
    return {"susceptible": list(susceptible), "resistant": list(resistant)}


def get_mutation_type(var_nom: str) -> tuple[str, Union[VariantSubType, str, int]]:
    """Extract mutation type from Mykrobe mutation description.

    GCG7569GTG -> mutation type, ref_nt, alt_nt, pos

    :param var_nom: Mykrobe mutation description
    :type var_nom: str
    :return: Return variant type, ref_nt, alt_ntt and position
    :rtype: dict[str, Union[VariantSubType, str, int]]
    """
    mut_type = None
    ref_nt = None
    alt_nt = None
    position = None
    try:
        ref_idx = re.search(r"\d", var_nom, 1).start()
        alt_idx = re.search(r"\d(?=[^\d]*$)", var_nom).start() + 1
    except AttributeError:
        return mut_type, ref_nt, alt_nt, position

    ref_nt = var_nom[:ref_idx]
    alt_nt = var_nom[alt_idx:]
    position = int(var_nom[ref_idx:alt_idx])
    var_len = abs(len(ref_nt) - len(alt_nt))
    if var_len >= 50:
        var_type = VariantType.SV
    elif 1 < var_len < 50:
        var_type = VariantType.INDEL
    else:
        var_type = VariantType.SNV
    if len(ref_nt) > len(alt_nt):
        var_sub_type = VariantSubType.DELETION
    elif len(ref_nt) < len(alt_nt):
        var_sub_type = VariantSubType.INSERTION
    else:
        var_sub_type = VariantSubType.SUBSTITUTION
    return {
        "type": var_type,
        "subtype": var_sub_type,
        "ref": ref_nt,
        "alt": alt_nt,
        "pos": position,
    }


def _parse_mykrobe_amr_variants(mykrobe_result) -> tuple[MykrobeVariant, ...]:
    """Get resistance genes from mykrobe result."""
    results = []

    for element_type in mykrobe_result:
        # skip non-resistance yeilding
        if not element_type["susceptibility"].upper() == "R":
            continue

        if element_type["variants"] is None:
            continue

        # generate phenotype info
        phenotype = [
            PhenotypeInfo(
                name=element_type["drug"],
                type=ElementType.AMR,
                annotation_type=AnnotationType.TOOL,
                annotation_author=Software.MYKROBE.value,
            )
        ]

        variants = element_type["variants"].split(";")
        # Mykrobe CSV variant format
        # <gene>_<aa change>-<nt change>:<ref depth>:<alt depth>:<gt confidence>
        # ref: https://github.com/Mykrobe-tools/mykrobe/wiki/AMR-prediction-output
        pattern = re.compile(
            r"(?P<gene>.+)_(?P<aa_change>.+)-(?P<dna_change>.+)"
            r":(?P<ref_depth>\d+):(?P<alt_depth>\d+):(?P<conf>\d+)",
            re.IGNORECASE,
        )
        for var_id, variant in enumerate(variants, start=1):
            # extract variant info using regex
            match_obj = re.search(pattern, variant).groupdict()

            # get type of variant
            var_aa = get_mutation_type(match_obj["aa_change"])
            # var_type, var_sub_type, ref_aa, alt_aa, _ = get_mutation_type(aa_change)

            # reduce codon to nt change for substitutions
            var_dna = get_mutation_type(match_obj["dna_change"])
            ref_nt, alt_nt = (var_dna["ref"], var_dna["alt"])
            if var_aa["subtype"] == VariantSubType.SUBSTITUTION:
                ref_nt, alt_nt = get_nt_change(ref_nt, alt_nt)

            # cast to variant object
            has_aa_change = all([len(var_aa["ref"]) == 1, len(var_aa["alt"]) == 1])
            variant = MykrobeVariant(
                # classification
                id=var_id,
                variant_type=var_aa["type"],
                variant_subtype=var_aa["subtype"],
                phenotypes=phenotype,
                # location
                reference_sequence=match_obj["gene"],
                start=var_dna["pos"],
                end=var_dna["pos"] + len(alt_nt),
                ref_nt=ref_nt,
                alt_nt=alt_nt,
                ref_aa=var_aa["ref"] if has_aa_change else None,
                alt_aa=var_aa["alt"] if has_aa_change else None,
                # variant info
                method=element_type["genotype_model"],
                depth=int(match_obj["ref_depth"]) + int(match_obj["alt_depth"]),
                frequency=int(match_obj["alt_depth"])
                / (int(match_obj["ref_depth"]) + int(match_obj["alt_depth"])),
                confidence=int(match_obj["conf"]),
                passed_qc=True,
            )
            results.append(variant)
    # sort variants
    variants = sorted(
        results, key=lambda entry: (entry.reference_sequence, entry.start)
    )
    return variants


def _read_result(result_path: str) -> Dict[str, Any]:
    """Read Mykrobe result file."""
    pred_res = pd.read_csv(result_path, quotechar='"')
    pred_res = (
        pred_res.rename(
            columns={pred_res.columns[3]: "variants", pred_res.columns[4]: "genes"}
        )
        .replace(["NA", np.nan], None)
        .to_dict(orient="records")
    )
    return pred_res


def get_version(result_path) -> SoupVersion:
    """Get version of Mykrobe from result."""
    LOG.debug("Get Mykrobe version")
    pred_res = _read_result(result_path)
    return SoupVersion(
        name="mykrobe-predictor",
        version=pred_res[0]["mykrobe_version"],
        type=SoupType.DB,
    )


def parse_amr_pred(
    result_path: str | Path, sample_id: str | None = None
) -> AMRMethodIndex | None:
    """Parse mykrobe resistance prediction results."""
    LOG.info("Parsing mykrobe prediction")
    pred_res = _read_result(result_path)
    # verify that sample id is in prediction result
    if sample_id is not None:
        if not sample_id in pred_res[0]["sample"]:
            LOG.warning(
                "Sample id %s is not in Mykrobe result, possible sample mixup",
                sample_id,
            )
            raise ValueError("Sample id is not in Mykrobe result.")

    resistance = ElementTypeResult(
        phenotypes=_get_mykrobe_amr_sr_profie(pred_res),
        genes=[],
        variants=_parse_mykrobe_amr_variants(pred_res),
    )

    # verify prediction result
    if is_prediction_result_empty(resistance):
        result = None
    else:
        result = AMRMethodIndex(
            type=ElementType.AMR, software=Software.MYKROBE, result=resistance
        )
    return result


def parse_spp_pred(result_path: str | Path) -> SppMethodIndex:
    """Get species prediction result from Mykrobe."""
    LOG.info("Parsing Mykrobe spp result.")
    result = []
    pred_res = _read_result(result_path)

    # Normalize all fields to strings and split on ";"
    species = str(pred_res[0].get("species", "")).split(";")
    phylo_groups = str(pred_res[0].get("phylo_group", "")).split(";")
    phylo_covg = str(pred_res[0].get("phylo_group_per_covg", "")).split(";")
    species_covg = str(pred_res[0].get("species_per_covg", "")).split(";")

    for hit_idx in range(len(species)):
        spp_pred = MykrobeSpeciesPrediction(
            scientific_name=species[hit_idx].replace("_", " "),
            taxonomy_id=None,
            phylogenetic_group=phylo_groups[hit_idx].replace("_", " "),
            phylogenetic_group_coverage=phylo_covg[hit_idx],
            species_coverage=species_covg[hit_idx],
        )
        result.append(spp_pred)
    return SppMethodIndex(software=SppPredictionSoftware.MYKROBE, result=result)


def parse_lineage_pred(result_path: str | Path) -> MethodIndex | None:
    """Parse mykrobe results for lineage object."""
    LOG.info("Parsing lineage results")
    pred_res = _read_result(result_path)
    if pred_res:
        lineage = pred_res[0]["lineage"]
        # cast to lineage object
        result_obj = ResultLineageBase(
            main_lineage=lineage.split(".")[0],
            sublineage=lineage,
        )
        return MethodIndex(
            type=TypingMethod.LINEAGE, software=Software.MYKROBE, result=result_obj
        )
    return None
