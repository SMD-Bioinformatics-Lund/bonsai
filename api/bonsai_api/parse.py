"""Functions for parsing results from prediction softwares."""

import logging
from enum import StrEnum

LOG = logging.getLogger(__name__)


class ChewbbacaErrors(StrEnum):
    """Chewbbaca error codes."""

    PLOT5 = "PLOT5"
    PLOT3 = "PLOT3"
    LOTSC = "LOTSC"
    NIPH = "NIPH"
    NIPHEM = "NIPHEM"
    ALM = "ALM"
    ASM = "ASM"
    LNF = "LNF"
    EXC = "EXC"
    PAMA = "PAMA"


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
            allele = allele.split("-")[1]
        else:
            allele = allele.replace("*", "")

    # try convert to an int
    try:
        allele = int(allele)
    except ValueError:
        allele = str(allele)
        LOG.warning(
            "Possible cgMLST parser error, allele could not be cast as an integer: %s",
            allele,
        )
    return allele
