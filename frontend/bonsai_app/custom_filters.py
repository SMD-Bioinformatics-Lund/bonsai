"""Custom jinja3 template tests."""

import logging
import math
import re
from zoneinfo import ZoneInfo
from collections import defaultdict
from itertools import chain
from typing import Any, Dict, List

from dateutil.parser import parse
from jsonpath2.path import Path as JsonPath

from .config import ANTIBIOTIC_CLASSES, settings
from .models import Severity, Tag, TagList, TagType, VirulenceTag

LOG = logging.getLogger(__name__)


def is_list(element: Any) -> bool:
    """Check if element is a list.

    :return: True if element is a list
    :rtype: bool
    """
    return isinstance(element, list)


def get_json_path(json_blob: Dict[str, Any], json_path: str) -> Any:
    """Get data from json object using a JSONpath

    JSONpath reference, https://github.com/json-path/JsonPath

    :param json_blob: python JSON object
    :type json_blob: Dict[str, Any]
    :param json_path: JSONpath
    :type json_path: str
    :return: JSON content
    :rtype: Any
    """
    jsonpath_expr = JsonPath.parse_str(json_path)
    for match in jsonpath_expr.match(json_blob):
        return match.current_value


def has_arg(amr_result, arg_name: str) -> bool:
    """Check if AMR prediction contains a gene with arg_name.

    :param amr_result: AMR prediction result from the db.
    :param arg_name: Resistance gene name
    :type arg_name: str
    :return: Return True if result contains gene name.
    :rtype: bool
    """
    for gene in amr_result["genes"]:
        if gene["name"] == arg_name:
            return True
    return False


def get_pvl_tag(vir_result) -> TagList:
    """Check if sample is PVL positive."""
    has_luks = any(gene["name"] == "lukS-PV" for gene in vir_result["genes"])
    has_lukf = any(gene["name"] == "lukF-PV" for gene in vir_result["genes"])

    # get the tags
    if has_lukf and has_luks:
        tag = Tag(
            type=TagType.VIRULENCE,
            label=VirulenceTag.PVL_ALL_POS,
            description="",
            severity=Severity.DANGER,
        )
    elif any([has_lukf and not has_luks, has_luks and not has_lukf]):
        tag = Tag(
            type=TagType.VIRULENCE,
            label=VirulenceTag.PVL_LUKF_POS if has_lukf else VirulenceTag.PVL_LUKS_POS,
            description="",
            severity=Severity.WARNING,
        )
    elif not has_lukf and not has_luks:
        tag = Tag(
            type=TagType.VIRULENCE,
            label=VirulenceTag.PVL_ALL_NEG,
            description="",
            severity=Severity.PASSED,
        )
    return tag


def get_all_phenotypes(res) -> str:
    """Get all phenotypes from phenotypic prediction.

    :param res: Prediction result
    :return: concatinated list of all phenotypes.
    :rtype: str
    """
    susceptible = res["result"]["phenotypes"]["susceptible"]
    resistant = res["result"]["phenotypes"]["resistant"]
    all_phenotypes = ", ".join(chain(susceptible, resistant))
    return f"All phenotypes: {all_phenotypes}"


def camelcase_to_text(text: str) -> str:
    """Convert camel_case to plain text.

    :param text: camel_case formatted text.
    :type text: str
    :return: Plain text text.
    :rtype: str
    """
    return text.replace("_", " ")


def text_to_camelcase(text: str) -> str:
    """Convert camel_case to plain text.

    :param text: camel_case formatted text.
    :type text: str
    :return: Plain text text.
    :rtype: str
    """
    return text.replace(" ", "_")


def _jinja2_filter_datetime(date: str, fmt: str = r"%Y-%m-%d") -> str:
    """Format date and time string using the timezone from settings.

    :param date: String representation of a date or time
    :type date: str
    :param fmt: formatting argument, defaults to None
    :type fmt: str, optional
    :return: reformatted datetime
    :rtype: str
    """
    date = parse(date)
    native = date.replace(tzinfo=ZoneInfo(settings.tz))
    return native.strftime(fmt)


def cgmlst_count_called(alleles: Dict[str, int | str | None]) -> int:
    """Return the number of called alleles

    Values other than integers are treated as failed calls and are not counted.

    :param alleles: called alleles
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


def nt_to_aa(nt_seq: str) -> str:
    """Translate nucleotide sequence to amino acid sequence.

    :param nt_seq: Nucleotide sequence.
    :type nt_seq: str
    :return: Amino acid sequence.
    :rtype: str
    """
    table = {
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
            aa_seq += table[codon]
    return aa_seq


def groupby_antib_class(antibiotics: List[str]) -> Dict[str, str]:
    """Group resistance genes on antibiotic class.

    :param antibiotics: List of antibiotics
    :type antibiotics: List[str]
    :return: Antibiotics grouped by antibiotic class
    :rtype: Dict[str, str]
    """
    antibiotic_class_lookup = {
        antib.lower(): k for k, v in ANTIBIOTIC_CLASSES for antib in v
    }
    result = defaultdict(list)
    for antib in antibiotics:
        antib_class = antibiotic_class_lookup.get(antib, "unknown")
        result[antib_class].append(antib)
    result = {k: result[k] for k in sorted(result)}
    return result


def fmt_number(num: int | float, sig_digits: int | None = None) -> str:
    """Format numbers by adding a thousand seperator.

    Has option to round values to C significant digits.

    100000 -> 100,000

    :param num: Number to format
    :type num: int | float
    :param sig_digits: Optional round to N digits, defaults to None
    :type sig_digits: int | None, optional
    :return: Rounded number with thousand seperator
    :rtype: str
    """
    if isinstance(num, (int, float)):
        if sig_digits is not None:
            num = round(num, sig_digits)
        num = f"{num:,}"
    return num


def fmt_null_values(value: int | str | None) -> int | str:
    """Replace null values with -."""
    if value is None:
        value = "–"
    return value


def has_same_analysis_profile(samples: List[Dict[str, Any]]) -> bool:
    """Check if all samples from session cache have the same analysis profile.

    :param samples: List of samples
    :type samples: List[Dict[str, Any]]
    :return: True if all samples have the same analysis profile.
    :rtype: bool
    """
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
    # sanity check the input number
    if not isinstance(number, (int, float)):
        LOG.debug("Got a non-number as input: %s", number)
        if number is None:
            return "-"
        else:
            return number

    # dont round zeroes
    if number == 0:
        return str(number)

    power = math.floor(math.log10(number))
    # source: https://sv.wikipedia.org/wiki/SI-prefix
    si_prefixes = {
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
    prefix = si_prefixes.get(order)
    if prefix:
        res = f"{short_number} {prefix[0]}"
    else:
        res = str(short_number)
    return res


def get_resistance_profile(prediction, level):
    """Get non redundant resistance profile."""
    result = []
    for res in prediction:
        fallback = res["name"]
        result.append(res.get(level, fallback).capitalize())
    return ", ".join(result)


def count_results(results, pred_type=None):
    """Count the number of prediction results of type."""
    if type is None:
        n_results = len(results)
    else:
        n_results = len([res for res in results if res["type"] == pred_type])
    return n_results


def n_results_with_resistance(results):
    """Count the number of prediction results yeilding resistance."""
    n_results = len([res for res in results if len(res["phenotypes"]) > 0])
    return n_results


def get_who_group_from_tbprofiler_comment(comment: Dict[str, str]) -> str | None:
    """Get WHO group from a comment from TbProfiler."""
    # annotate WHO classification
    who_classes = {
        "assoc w r": 1,
        "assoc w r - interim": 2,
        "uncertain significance": 3,
        "not assoc w r - interim": 4,
        "not assoc w r": 5,
    }
    if isinstance(comment["note"], str):
        who_group = who_classes.get(comment["note"].lower())
        if who_group is not None:
            return f"{who_group}"
    return None


def format_tbprofiler_db_annotation(comment: Dict[str, str]) -> str:
    """Shorten TbProfiler source annotation."""
    db_names = {
        "tbdb": "TBDB",
        "fohm": "Fohm",
    }
    annot_source = comment["source"].lower()
    who_match = re.search(r"^who.*v(\d+)", annot_source)
    if annot_source in db_names:
        fmt_name = db_names[annot_source]
    elif who_match:
        version = who_match.group(1)
        fmt_name = f"WHOv{version}"
    else:
        fmt_name = annot_source
    return fmt_name


TESTS = {
    "list": is_list,
}

FILTERS = {
    "json_path": get_json_path,
    "has_arg": has_arg,
    "get_all_phenotypes": get_all_phenotypes,
    "camelcase_to_text": camelcase_to_text,
    "text_to_camelcase": text_to_camelcase,
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
    "get_resistance_profile": get_resistance_profile,
    "count_results": count_results,
    "n_results_with_resistance": n_results_with_resistance,
    "lookup_who_group": get_who_group_from_tbprofiler_comment,
    "fmt_db_annotation": format_tbprofiler_db_annotation,
}
