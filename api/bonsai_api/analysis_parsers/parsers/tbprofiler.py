"""Parse TBprofiler result."""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from ..models.metadata import SoupType, SoupVersion
from ..models.phenotype import (
    AMRMethodIndex,
    AnnotationType,
    ElementType,
    ElementTypeResult,
    PhenotypeInfo,
)
from ..models.phenotype import PredictionSoftware as Software
from ..models.phenotype import TbProfilerVariant, VariantSubType, VariantType
from ..models.sample import MethodIndex
from ..models.typing import LineageInformation, TbProfilerLineage, TypingMethod
from .utils import get_db_version

LOG = logging.getLogger(__name__)
EXPECTED_SCHEMA_VERSION = "1.0.0"


def _read_result(path: Path, strict: bool = False) -> Dict[str, Any]:
    """Read TbProfiler output."""
    with path.open("r", encoding="utf-8") as tbprofiler_json:
        pred_res = json.load(tbprofiler_json)
        # check schema version
        schema_version = pred_res.get("schema_version")
        if not EXPECTED_SCHEMA_VERSION == schema_version:
            LOG.warning(
                (
                    "Unsupported TbProfiler schema version - ",
                    "output might be inaccurate; ",
                    "result schema: %s; expected: %s",
                ),
                schema_version,
                EXPECTED_SCHEMA_VERSION,
            )
            if strict:
                raise ValueError("Unsupported version of TbProfiler output.")
    return pred_res


def _get_tbprofiler_amr_sr_profie(tbprofiler_result):
    """Get tbprofiler susceptibility/resistance profile."""
    susceptible = set()
    resistant = set()
    drugs = [
        "ofloxacin",
        "moxifloxacin",
        "isoniazid",
        "delamanid",
        "kanamycin",
        "amikacin",
        "ethambutol",
        "ethionamide",
        "streptomycin",
        "ciprofloxacin",
        "levofloxacin",
        "pyrazinamide",
        "linezolid",
        "rifampicin",
        "capreomycin",
    ]

    if not tbprofiler_result:
        return {}

    for hit in tbprofiler_result["dr_variants"]:
        for drug in hit["gene_associated_drugs"]:
            resistant.add(drug)
    susceptible = [drug for drug in drugs if drug not in resistant]
    return {"susceptible": list(susceptible), "resistant": list(resistant)}


def _parse_tbprofiler_amr_variants(predictions) -> tuple[TbProfilerVariant, ...]:
    """Get resistance genes from tbprofiler result."""
    variant_caller = None
    for prog in predictions["pipeline"]["software"]:
        if prog["process"].lower() == "variant_calling":
            variant_caller = prog["software"]
    results = []

    # tbprofiler report three categories of variants
    # - dr_variants: known resistance variants
    # - qc_fail_variants: known resistance variants failing qc
    # - other_variants: variants not in the database but in genes
    #                   associated with resistance
    var_id = 1
    for result_type in ["dr_variants", "other_variants", "qc_fail_variants"]:
        # associated with passed/ failed qc
        if result_type == "qc_fail_variants":
            passed_qc = False
        else:
            passed_qc = True

        # parse variants
        for hit in predictions.get(result_type, []):
            ref_nt = hit["ref"]
            alt_nt = hit["alt"]
            var_type = VariantType.SNV if not bool(hit["sv"]) else VariantType.SV
            var_len = abs(len(ref_nt) - len(alt_nt))
            if var_len >= 50 or bool(hit["sv"]):
                var_type = VariantType.SV
            elif 1 < var_len < 50:
                var_type = VariantType.INDEL
            else:
                var_type = VariantType.SNV
            if len(ref_nt) == len(alt_nt):
                var_sub_type = VariantSubType.SUBSTITUTION
            elif len(ref_nt) > len(alt_nt):
                var_sub_type = VariantSubType.DELETION
            else:
                var_sub_type = VariantSubType.INSERTION

            variant = TbProfilerVariant(
                # classificatoin
                id=var_id,
                variant_type=var_type,
                variant_subtype=var_sub_type,
                phenotypes=parse_drug_resistance_info(hit.get("annotation", [])),
                # location
                reference_sequence=hit["gene_name"],
                accession=hit["feature_id"],
                start=int(hit["pos"]),
                end=int(hit["pos"]) + len(alt_nt),
                ref_nt=ref_nt,
                alt_nt=alt_nt,
                # consequense
                variant_effect=hit["type"],
                hgvs_nt_change=hit["nucleotide_change"],
                hgvs_aa_change=hit["protein_change"],
                # prediction info
                depth=hit["depth"],
                frequency=float(hit["freq"]),
                method=variant_caller,
                passed_qc=passed_qc,
            )
            var_id += 1  # increment variant id
            results.append(variant)
    # sort variants
    variants = sorted(
        results, key=lambda entry: (entry.reference_sequence, entry.start)
    )
    return variants


def parse_drug_resistance_info(drugs: list[dict[str, str]]) -> list[PhenotypeInfo]:
    """Parse drug info into the standard format.

    :param drugs: TbProfiler drug info
    :type drugs: list[dict[str, str]]
    :return: Formatted phenotype info
    :rtype: list[PhenotypeInfo]
    """
    phenotypes = []
    for drug in drugs:
        # assign element type
        if drug["type"] == "drug_resistance" or drug["type"] == "who_confidence":
            drug_type = ElementType.AMR
        else:
            drug_type = ElementType.AMR
            LOG.warning(
                (
                    "Unknown TbProfiler drug; drug: %s"
                    ", confers resistance with confidence"
                    ": %s; default to %s"
                ),
                drug["type"],
                drug["confidence"],
                drug_type,
            )
        reference = drug.get("comment")
        phenotypes.append(
            PhenotypeInfo(
                name=drug["drug"],
                type=drug_type,
                reference=[] if reference is None else [reference],
                annotation_type=AnnotationType.TOOL,
                annotation_author=Software.TBPROFILER.value,
                note=drug.get("confidence"),
                source=drug.get("source"),
            )
        )
    return phenotypes


def get_version(result_path) -> SoupVersion:
    """Get version of Mykrobe from result."""
    LOG.debug("Get Mykrobe version")
    pred_res = _read_result(result_path)
    version = SoupVersion(
        name=pred_res["pipeline"]["db_version"]["name"],
        version=get_db_version(pred_res["pipeline"]["db_version"]),
        type=SoupType.DB,
    )
    return version


def parse_amr_pred(path: Path) -> AMRMethodIndex:
    """Parse tbprofiler resistance prediction results."""
    LOG.info("Parsing tbprofiler prediction")
    prediction = _read_result(path)
    resistance = ElementTypeResult(
        phenotypes=_get_tbprofiler_amr_sr_profie(prediction),
        genes=[],
        variants=_parse_tbprofiler_amr_variants(prediction),
    )
    return AMRMethodIndex(
        type=ElementType.AMR, software=Software.TBPROFILER, result=resistance
    )


def parse_lineage_pred(path: Path) -> MethodIndex:
    """Parse tbprofiler results for lineage object."""
    LOG.info("Parsing lineage results")
    pred_res = _read_result(path)
    # lineages
    lineages = [
        LineageInformation(
            lineage=lin["lineage"],
            family=lin["family"],
            rd=lin["rd"],
            fraction=lin["fraction"],
            support=lin["support"],
        )
        for lin in pred_res["lineage"]
    ]
    # combine into result
    result_obj = TbProfilerLineage(
        main_lineage=pred_res["main_lineage"],
        sublineage=pred_res["sub_lineage"],
        lineages=lineages,
    )
    # store result as a method index
    return MethodIndex(
        type=TypingMethod.LINEAGE,
        software=Software.TBPROFILER,
        result=result_obj,
    )
