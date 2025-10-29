"""Parsers for various typing tools."""

import csv
import json
import logging

from ..models.sample import MethodIndex
from ..models.typing import (
    ChewbbacaErrors,
    TypingMethod,
    TypingResultCgMlst,
    TypingResultMlst,
)
from ..models.typing import TypingSoftware as Software

alt_allele_calls = ["ALM", "ASM", "EXC", "INF", "LNF", "LOTSC ", "NIPH", "NIPHEM", "PAMA", "PLNF", "PLOT3", "PLOT5"]

LOG = logging.getLogger(__name__)


def _process_allele_call(allele: str) -> str | list[str] | None:
    if allele.isdigit():
        result = int(allele)
    elif "," in allele:
        result = allele.split(",")
    elif "?" in allele:
        result = "partial"
    elif "~" in allele:
        result = "novel"
    elif allele == "-":
        result = None
    else:
        raise ValueError(f"MLST allele {allele} not expected format")
    return result


def parse_mlst_results(mlst_fpath: str) -> MethodIndex:
    """Parse mlst results from mlst to json object."""
    LOG.info("Parsing mlst results")
    with open(mlst_fpath, "r", encoding="utf-8") as jsonfile:
        result = json.load(jsonfile)[0]
        # get raw allele info
        alleles = {} if result.get("alleles") is None else result["alleles"]
        # create typing result object
        result_obj = TypingResultMlst(
            scheme=result["scheme"],
            sequence_type=(
                None if result["sequence_type"] == "-" else result["sequence_type"]
            ),
            alleles={
                gene: _process_allele_call(allele) for gene, allele in alleles.items()
            },
        )
    return MethodIndex(
        type=TypingMethod.MLST, software=Software.MLST, result=result_obj
    )


def replace_cgmlst_errors(
    allele: str, include_novel_alleles: bool = True, correct_alleles: bool = False
) -> int | str | None:
    """Replace errors and novel allele calls with null values."""
    errors = [err.value for err in ChewbbacaErrors]
    # check input
    match allele:
        case str():
            pass
        case int():
            allele = str(allele)
        case bool():
            allele = str(int(allele))
        case _:
            raise ValueError(f"Unknown file type: {allele}")
    if any(
        [
            correct_alleles and allele in errors,
            correct_alleles and allele.startswith("INF") and not include_novel_alleles,
        ]
    ):
        return None

    if include_novel_alleles:
        if allele.startswith("INF"):
            allele = allele.split("-")[1].replace("*", "")
        else:
            allele = allele.replace("*", "")

    # try convert to an int
    try:
        allele = int(allele)
    except ValueError:
        allele = str(allele)
        if allele not in alt_allele_calls:
            LOG.warning(
                "Possible cgMLST parser error, allele could not be cast as an integer: %s",
                allele,
            )
    return allele


def parse_cgmlst_results(
    chewbacca_res_path: str,
    include_novel_alleles: bool = True,
) -> MethodIndex:
    """Parse chewbbaca cgmlst prediction results to json results.

    Chewbbaca reports errors in allele profile.
    See: https://github.com/B-UMMI/chewBBACA
    -------------------
    INF-<allele name>, inferred new allele
    LNF, loci not found
    PLOT, loci contig tips
    NIPH, non-informative paralogous hits
    NIPHEM,
    ALM, alleles larger than locus length
    ASM, alleles smaller than locus length
    EXC, Total number of CDSs classified as EXC
    LOTSC, Total number of CDSs classified as LOTSC
    PAMA, Total number of PAMA classifications
    """

    errors = [err.value for err in ChewbbacaErrors]
    LOG.info(
        "Parsing cgmslt results, %s including novel alleles",
        "not" if not include_novel_alleles else "",
    )

    with open(chewbacca_res_path, encoding="utf-8") as fileh:
        creader = csv.reader(fileh, delimiter="\t")
        _, *allele_names = (colname.rstrip(".fasta") for colname in next(creader))
        # parse alleles
        _, *alleles = next(creader)

    # setup counters for counting novel and missing alleles before correction
    n_novel = 0

    n_missing = 0
    corrected_alleles = []
    for allele in alleles:
        if allele.startswith("INF") or allele.startswith("*"):
            n_novel += 1
        if allele in errors:
            n_missing += 1
        corrected_alleles.append(replace_cgmlst_errors(allele))

    results = TypingResultCgMlst(
        n_novel=n_novel,
        n_missing=n_missing,
        alleles=dict(zip(allele_names, corrected_alleles)),
    )
    return MethodIndex(
        type=TypingMethod.CGMLST, software=Software.CHEWBBACA, result=results
    )
