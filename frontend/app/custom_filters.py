"""Custom jinja3 template tests."""
import logging
import math
from collections import defaultdict
from itertools import chain
from typing import Dict

from dateutil.parser import parse
from jsonpath2.path import Path as JsonPath

from .config import ANTIBIOTIC_CLASSES
from .models import TAG_LIST, Severity, Tag, TagType, VirulenceTag

LOG = logging.getLogger(__name__)


def is_list(value) -> bool:
    """Check if value is a list"""
    return isinstance(value, list)


def json_path(json_blob, json_path):
    """Get data from json blob with JSONpath."""
    jsonpath_expr = JsonPath.parse_str(json_path)
    for match in jsonpath_expr.match(json_blob):
        return match.current_value


def has_arg(amr_result, arg_name: str) -> bool:
    """Check if an antimicrobial resistance gene with NAME has been predicted."""
    # next(JsonPath.parse_str("$.typingResult[?(@.type='mlst')]").match(json_blob)).current_value
    for gene in amr_result["genes"]:
        if gene["name"] == arg_name:
            return True
    return False


def get_pvl_tag(vir_result) -> TAG_LIST:
    """Check if sample is PVL positive."""
    has_lukS = any(gene["name"] == "lukS-PV" for gene in vir_result["genes"])
    has_lukF = any(gene["name"] == "lukF-PV" for gene in vir_result["genes"])

    # get the tags
    if has_lukF and has_lukS:
        tag = Tag(
            type=TagType.VIRULENCE,
            label=VirulenceTag.PVL_ALL_POS,
            description="",
            severity=Severity.DANGER,
        )
    elif any([has_lukF and not has_lukS, has_lukS and not has_lukF]):
        tag = Tag(
            type=TagType.VIRULENCE,
            label=VirulenceTag.PVL_LUKF_POS if has_lukF else VirulenceTag.PVL_LUKS_POS,
            description="",
            severity=Severity.WARNING,
        )
    elif not has_lukF and not has_lukS:
        tag = Tag(
            type=TagType.VIRULENCE,
            label=VirulenceTag.PVL_ALL_NEG,
            description="",
            severity=Severity.PASSED,
        )
    return tag


def get_all_phenotypes(res):
    susceptible = res["result"]["phenotypes"]["susceptible"]
    resistant = res["result"]["phenotypes"]["resistant"]
    all_phenotypes = ", ".join(chain(susceptible, resistant))
    return f"All phenotypes: {all_phenotypes}"


def camelcase_to_text(text):
    return text.replace("_", " ")


def _jinja2_filter_datetime(date, fmt=None):
    date = parse(date)
    native = date.replace(tzinfo=None)
    format = "%b %d, %Y"
    return native.strftime(format)


def cgmlst_count_called(alleles: Dict[str, int | str | None]) -> int:
    """Return the number of called allleles

    :param alleles: called allleles
    :type alleles: Dict[str, int | str | None]
    :return: The number of called alleles
    :rtype: int
    """
    return sum(1 for allele in alleles.values() if isinstance(allele, int))


def cgmlst_count_missing(alleles: Dict[str, int | str | None]) -> int:
    """Count the number of missing alleles.

    Strings and null values are treated as failed calls.

    :param alleles: called alleles
    :type alleles: Dict[str, int  |  str  |  None]
    :return: Number of missing alleles
    :rtype: int
    """
    return sum(
        1 for allele in alleles.values() if isinstance(allele, str) or allele is None
    )


def nt_to_aa(nt_seq):
    """Translate nucleotide sequence to aa sequence"""
    TABLE = {
        "TTT": "F",
        "TTC": "F",
        "TTA": "L",
        "TTG": "L",
        "TCT": "S",
        "TCC": "S",
        "TCA": "S",
        "TCG": "S",
        "TAT": "Y",
        "TAC": "Y",  # noqa: E241
        "TGT": "C",
        "TGC": "C",
        "TGG": "W",  # noqa: E241
        "CTT": "L",
        "CTC": "L",
        "CTA": "L",
        "CTG": "L",
        "CCT": "P",
        "CCC": "P",
        "CCA": "P",
        "CCG": "P",
        "CAT": "H",
        "CAC": "H",
        "CAA": "Q",
        "CAG": "Q",
        "CGT": "R",
        "CGC": "R",
        "CGA": "R",
        "CGG": "R",
        "ATT": "I",
        "ATC": "I",
        "ATA": "I",
        "ATG": "M",
        "ACT": "T",
        "ACC": "T",
        "ACA": "T",
        "ACG": "T",
        "AAT": "N",
        "AAC": "N",
        "AAA": "K",
        "AAG": "K",
        "AGT": "S",
        "AGC": "S",
        "AGA": "R",
        "AGG": "R",
        "GTT": "V",
        "GTC": "V",
        "GTA": "V",
        "GTG": "V",
        "GCT": "A",
        "GCC": "A",
        "GCA": "A",
        "GCG": "A",
        "GAT": "D",
        "GAC": "D",
        "GAA": "E",
        "GAG": "E",
        "GGT": "G",
        "GGC": "G",
        "GGA": "G",
        "GGG": "G",
    }
    stop_codons = (["TAA", "TAG", "TGA"],)
    start_codons = (["TTG", "CTG", "ATT", "ATC", "ATA", "ATG", "GTG"],)
    aa_seq = ""
    for pos in range(0, len(nt_seq), 3):
        codon = nt_seq[pos : pos + 3].upper()
        if codon in start_codons:
            aa_seq += "START"
        elif codon in stop_codons:
            aa_seq += "STOP"
        else:
            aa_seq += TABLE[codon]
    return aa_seq


def groupby_antib_class(antibiotics):
    # todo lookup antibiotic classes in database
    antibiotic_class_lookup = {
        antib.lower(): k for k, v in ANTIBIOTIC_CLASSES for antib in v
    }
    result = defaultdict(list)
    for antib in antibiotics:
        antib_class = antibiotic_class_lookup.get(antib, "unknown")
        result[antib_class].append(antib)
    result = {k: result[k] for k in sorted(result)}
    return result


def fmt_number(num, sig_digits=None):
    """Format number by adding a thousand separator

    Has option to round values to X signifiacnt digits."""
    if isinstance(num, (int, float)):
        if sig_digits is not None:
            num = round(num, sig_digits)
        num = "{:,}".format(num)
    return num


def fmt_null_values(value):
    """Replace null values with -."""
    if value is None:
        value = "–"
    return value


def has_same_analysis_profile(samples):
    """Check if all samples from session cache have the same analysis profile."""
    profiles = [sample["analysis_profile"] for sample in samples]
    return len(set(profiles)) == 1


def human_readable_large_numbers(number: float, decimals: int = 2) -> str:
    """Large number to human readable version.

    E.g 2345000 -> 2.35 Mega

    :param number: large number to convert
    :type number: float
    :param decimals: number of decimals to round number to, defaults to 2
    :type decimals: int, optional
    :return: rounded human readable number with SI prefix
    :rtype: str
    """
    power = math.floor(math.log10(number))
    # source: https://sv.wikipedia.org/wiki/SI-prefix
    SI_PREFIXES = {
        1: "Kilo",
        2: "Mega",
        3: "Giga",
        4: "Tera",
        5: "Peta",
        6: "Exa",
        7: "Zetta",
        8: "Yotta",
        9: "Ronna",
        10: "Quetta",
    }
    order = power // 3
    # long number to rounded short number, 1230 -> 1.23 Kilo
    short_number = round(number / math.pow(10, 3 * order), decimals)
    prefix = SI_PREFIXES[order]
    return f"{short_number} {prefix[0]}"


TESTS = {
    "list": is_list,
}

FILTERS = {
    "json_path": json_path,
    "has_arg": has_arg,
    "get_all_phenotypes": get_all_phenotypes,
    "camelcase_to_text": camelcase_to_text,
    "strftime": _jinja2_filter_datetime,
    "cgmlst_count_called": cgmlst_count_called,
    "cgmlst_count_missing": cgmlst_count_missing,
    "nt_to_aa": nt_to_aa,
    "groupby_antib_class": groupby_antib_class,
    "fmt_number": fmt_number,
    "fmt_null_values": fmt_null_values,
    "has_same_analysis_profile": has_same_analysis_profile,
    "get_pvl_tag": get_pvl_tag,
    "fmt_to_human_readable": human_readable_large_numbers,
}
