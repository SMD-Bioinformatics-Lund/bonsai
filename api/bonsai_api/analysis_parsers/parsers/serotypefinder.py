"""Functions for parsing serotypefinder result."""

import json
import logging
from typing import Any

from ..models.phenotype import ElementSerotypeSubtype, ElementType, SerotypeGene
from ..models.sample import MethodIndex
from ..models.typing import TypingResultGeneAllele
from ..models.typing import TypingSoftware as Software

LOG = logging.getLogger(__name__)


def parse_serotype_gene(
    info: dict[str, Any],
    subtype: ElementSerotypeSubtype = ElementSerotypeSubtype.ANTIGEN,
) -> SerotypeGene:
    """Parse serotype gene prediction results."""
    start_pos, end_pos = map(int, info["position_in_ref"].split(".."))
    # Some genes doesnt have accession numbers
    accnr = None if info["accession"] == "NA" else info["accession"]
    return SerotypeGene(
        # info
        gene_symbol=info["gene"],
        accession=accnr,
        sequence_name=info["serotype"],
        # gene classification
        element_type=ElementType.ANTIGEN,
        element_subtype=subtype,
        # position
        ref_start_pos=start_pos,
        ref_end_pos=end_pos,
        ref_gene_length=info["template_length"],
        alignment_length=info["HSP_length"],
        # prediction
        identity=info["identity"],
        coverage=info["coverage"],
    )


def parse_oh_typing(path: str) -> MethodIndex | None:
    """Parse 's output re OH typing"""
    LOG.info("Parsing serotypefinder oh type results")
    with open(path, "rb") as inpt:
        pred_obj = json.load(inpt)
        # if has valid results
        pred_result = []
        if "serotypefinder" in pred_obj:
            results = pred_obj["serotypefinder"]["results"]
            for serotype in results:
                # if no serotype gene was identified
                if isinstance(results[serotype], str) or results[serotype] == {}:
                    continue

                # take first result as the valid prediction
                hit = next(iter(results[serotype].values()))
                vir_gene = parse_serotype_gene(hit)
                gene = TypingResultGeneAllele(**vir_gene.model_dump())
                pred_result.append(
                    MethodIndex(
                        type=serotype,
                        software=Software.SEROTYPEFINDER,
                        result=gene,
                    )
                )
    return pred_result
