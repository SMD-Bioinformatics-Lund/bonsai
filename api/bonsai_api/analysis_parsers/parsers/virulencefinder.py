"""Functions for parsing virulencefinder result."""

import json
import logging
from typing import Any

from ..models.phenotype import ElementType, ElementVirulenceSubtype
from ..models.phenotype import PredictionSoftware as Software
from ..models.phenotype import (
    VirulenceElementTypeResult,
    VirulenceGene,
    VirulenceMethodIndex,
)
from ..models.sample import MethodIndex
from ..models.typing import TypingMethod, TypingResultGeneAllele

LOG = logging.getLogger(__name__)


def parse_vir_gene(
    info: dict[str, Any], function: str, subtype: ElementVirulenceSubtype = ElementVirulenceSubtype.VIR
) -> VirulenceGene:
    """Parse virulence gene prediction results."""
    accnr = info.get("ref_acc", None)
    if accnr == "NA":
        accnr = None
    return VirulenceGene(
        # info
        gene_symbol=info["name"],
        accession=accnr,
        sequence_name=function,
        # gene classification
        element_type=ElementType.VIR,
        element_subtype=subtype,
        # position
        ref_start_pos=int(info["ref_start_pos"]),
        ref_end_pos=int(info["ref_end_pos"]),
        ref_gene_length=int(info["ref_seq_length"]),
        alignment_length=int(info["alignment_length"]),
        # prediction
        identity=float(info["identity"]),
        coverage=float(info["coverage"]),
    )


def _parse_vir_results(pred: dict[str, Any]) -> VirulenceElementTypeResult:
    """Parse virulence prediction results from virulencefinder."""
    vir_genes = []

    phenotypes = pred.get("phenotypes", {})
    seq_regions = pred.get("seq_regions", {})
    
    for key, pheno in phenotypes.items():
        function = pheno.get("function")
        ref_dbs = pheno.get("ref_database", [])

        # skip stx typing result
        if any("stx" in db for db in ref_dbs):
            continue

        # assign element subtype
        subtype = ElementVirulenceSubtype.VIR
        if any("toxin" in db for db in ref_dbs):
            subtype = ElementVirulenceSubtype.TOXIN

        # parse genes
        for region_key in pheno.get("seq_regions", []):
            seq_info = seq_regions.get(region_key)
            if not seq_info:
                continue
            vir_genes.append(parse_vir_gene(seq_info, subtype=subtype, function=function))
    # sort genes
    genes = sorted(vir_genes, key=lambda entry: (entry.gene_symbol, entry.coverage))
    return VirulenceElementTypeResult(genes=genes, phenotypes={}, variants=[])


def parse_virulence_pred(path: str) -> VirulenceMethodIndex | None:
    """Parse virulencefinder virulence prediction results.

    :param file: File name
    :type file: str
    :return: Return element type if virulence was predicted else null
    :rtype: ElementTypeResult | None
    """
    LOG.info("Parsing virulencefinder virulence prediction")
    with open(path, "rb") as inpt:
        pred = json.load(inpt)
        if "seq_regions" in pred and "phenotypes" in pred: # Aim: check if file is empty or if it comes from the right tool?
            results: VirulenceElementTypeResult = _parse_vir_results(pred)
            result = VirulenceMethodIndex(
                type=ElementType.VIR, software=Software.VIRFINDER, result=results
            )
        else:
            result = None
    return result


def parse_stx_typing(path: str) -> MethodIndex | None:
    """Parse virulencefinder's output re stx typing"""
    LOG.info("Parsing virulencefinder stx results")
    with open(path, "rb") as inpt:
        pred_obj = json.load(inpt)
        # if has valid results
        pred_result = None
        if "seq_regions" in pred_obj and "phenotypes" in pred_obj:
            phenotypes = pred_obj.get("phenotypes", {})
            seq_regions = pred_obj.get("seq_regions", {})
    
            stx_keys = [key for key in phenotypes if key.startswith("stx")]
            if not stx_keys:
                return None
            
            for stx_key in stx_keys:
                pheno = phenotypes[stx_key]
                function = pheno.get("function", "")
                for region_key in pheno.get("seq_regions", []):
                    region_info = seq_regions.get(region_key)
                    if region_info:
                        vir_gene = parse_vir_gene(region_info, function=function)
                        # TODO cleanup data models. They are too inherited which makes it difficult to know what fields they contain
                        gene = TypingResultGeneAllele(**vir_gene.model_dump())
                        return MethodIndex(
                            type=TypingMethod.STX,
                            software=Software.VIRFINDER,
                            result=gene,
                        )
    return pred_result
