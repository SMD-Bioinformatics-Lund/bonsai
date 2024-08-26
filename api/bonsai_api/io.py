"""File IO operations."""
import itertools
import logging
import mimetypes
import os
import pathlib
import re
from collections import defaultdict
from enum import Enum
from typing import List, Tuple

import pandas as pd
from fastapi.responses import Response
from prp.models.phenotype import GeneBase, PredictionSoftware, VariantBase
from prp.models.typing import TypingMethod

from .models.qc import SampleQcClassification
from .models.sample import SampleInDatabase

LOG = logging.getLogger(__name__)
BYTE_RANGE_RE = re.compile(r"bytes=(\d+)-(\d+)?$")

TARGETED_ANTIBIOTICS = {
    "rifampicin": {"abbrev": "rif", "split_res_level": False},
    "isoniazid": {"abbrev": "inh", "split_res_level": True},
    "pyrazinamide": {"abbrev": "pyr", "split_res_level": False},
    "ethambutol": {"abbrev": "etb", "split_res_level": False},
    "amikacin": {"abbrev": "ami", "split_res_level": False},
    "levofloxacin": {"abbrev": "lev", "split_res_level": False},
}


class TBResponses(Enum):
    """Valid responses for M. tuberculosis results."""

    resistant = "Mutation påvisad"
    susceptible = "Mutation ej påvisad"
    sample_failed = "Ej bedömbart"


class InvalidRangeError(Exception):
    """Exception for retrieving invalid file ranges."""


class RangeOutOfBoundsError(Exception):
    """Exception if range is out of bounds."""


def is_file_readable(file_path: str) -> bool:
    """Check if file exist and is readable.

    :param file_path: File path object
    :type file_path: str
    :return: True if readable and exist
    :rtype: bool
    """
    path = pathlib.Path(file_path)
    if not path.is_file():
        LOG.warning("trying to access missing reference genome data: %s", file_path)
        raise FileNotFoundError(file_path)

    if not os.access(path, os.R_OK):
        LOG.warning("file: %s cant read by the system user", file_path)
        raise PermissionError(file_path)

    return True


def parse_byte_range(byte_range: str) -> Tuple[int, int]:
    """Returns the two numbers in 'bytes=123-456' or throws ValueError.
    The last number or both numbers may be None.
    """
    if byte_range.strip() == "":
        return None, None

    m = BYTE_RANGE_RE.match(byte_range)
    if not m:
        raise InvalidRangeError(f"Invalid byte range {byte_range}")

    first, last = [x and int(x) for x in m.groups()]
    if last and last < first:
        raise InvalidRangeError(f"Invalid byte range {byte_range}")
    return first, last


def send_partial_file(path: str, range_header: str) -> Response:
    """Send partial file as a response.

    :param path: File path
    :type path: str
    :param range_header: byte range, ie bytes=123-456
    :type range_header: str
    :raises RangeOutOfBoundsError: Error if the byte range is out of bounds.
    :return: Exception
    :rtype: Response
    """
    byte_range = parse_byte_range(range_header)
    first, last = byte_range

    data = None
    with open(path, "rb") as file_handle:
        fs = os.fstat(file_handle.fileno())
        file_len = fs[6]
        if first >= file_len:
            raise RangeOutOfBoundsError("Requested Range Not Satisfiable")

        if last is None or last >= file_len:
            last = file_len - 1
        response_length = last - first + 1

        file_handle.seek(first)
        data = file_handle.read(response_length)

    response_headers = {
        "Content-type": "application/octet-stream",
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {first}-{last}/{file_len}",
        "Content-Length": str(response_length),
    }
    return Response(
        content=data,
        status_code=206,
        media_type=mimetypes.guess_type(path)[0],
        headers=response_headers,
    )


def _sort_motifs_on_phenotype(prediction: List[GeneBase | VariantBase]):
    """Sort resistance genes and variants by the antibiotics they yeid resistance to."""
    result = defaultdict(lambda: defaultdict(list))
    for motif in prediction:
        if len(motif.phenotypes) == 0:
            result["none"]["none"].append(motif)
        else:
            # add variant to all phenotypes
            for phenotype in motif.phenotypes:
                # make a copy with only one phenotypes
                upd_motif = motif.model_copy(update={"phenotypes": [phenotype]})
                result[phenotype.name][phenotype.resistance_level].append(upd_motif)
    return result


def _fmt_variant(variant):
    """Format information of a resistance variant."""
    who_classes = {
        "Assoc w R": 1,
        "Assoc w R - Interim": 2,
        "Uncertain significance": 3,
        "Not assoc w R - Interim": 4,
        "Not assoc w R": 5,
    }
    var_type = variant.variant_type
    if var_type == "SV":
        variant_desc = (
            f"g.{variant.start}_{variant.end}{variant.variant_subtype.lower()}"
        )
    else:
        variant_name = (
            variant.hgvs_nt_change
            if variant.hgvs_aa_change == ""
            else variant.hgvs_aa_change
        )
        variant_desc = f"{variant.reference_sequence}.{variant_name}"
    # annotate variant frequency for minority variants
    if variant.frequency is not None and variant.frequency < 1:
        variant_desc = f"{variant_desc}({variant.frequency * 100:.1f}%)"
    # annotate WHO classification
    who_group = who_classes.get(variant.phenotypes[0].note)
    if who_group is not None:
        variant_desc = f"{variant_desc} WHO-{who_group}"
    return variant_desc


def _fmt_mtuberculosis(sample: SampleInDatabase):
    """Format M. tuberculosis result.

    - one row per antibiotic with all variants

    :param sample: Prediction results
    :type sample: SampleInDatabase
    """
    has_failed = (
        sample.qc_status.status == "failed"
        and sample.qc_status.action == "permanent fail"
    )
    result = []
    for pred_res in sample.element_type_result:
        # only include TBprofiler result
        if not pred_res.software == PredictionSoftware.TBPROFILER:
            continue

        # combine tbprofiler variants, called SNV and called SV
        sv_variants = sample.sv_variants if sample.sv_variants is not None else []
        snv_variants = sample.snv_variants if sample.snv_variants is not None else []
        filtered_variants = [
            var
            for var in itertools.chain(
                pred_res.result.variants, sv_variants, snv_variants
            )
            if var.verified == "passed"
        ]
        # reformat predicted resistance
        sorted_variants = _sort_motifs_on_phenotype(filtered_variants)

        # create tabular result
        for antibiotic, info in TARGETED_ANTIBIOTICS.items():
            # concat variants
            if info["split_res_level"]:
                for lvl in ["high", "low"]:
                    abbrev = info["abbrev"]
                    if (
                        antibiotic in sorted_variants
                        and len(sorted_variants[antibiotic][lvl]) > 0
                    ):
                        call = TBResponses.resistant.value
                        variants = ";".join(
                            _fmt_variant(var)
                            for var in sorted_variants[antibiotic][lvl]
                        )
                    else:
                        # add non-called resistance
                        call = TBResponses.susceptible.value
                        variants = "-"
                    result.append(
                        {
                            "sample_id": sample.run_metadata.run.sample_name,
                            "parameter": f"{abbrev.upper()}_NGS{lvl[0].upper()}",
                            "result": call,
                            "variants": variants,
                        }
                    )
            else:
                if antibiotic in sorted_variants:
                    call = TBResponses.resistant.value
                    combined_variants = itertools.chain(
                        *sorted_variants[antibiotic].values()
                    )
                    variants = ";".join(_fmt_variant(var) for var in combined_variants)
                else:
                    # add non-called resistance
                    call = TBResponses.susceptible.value
                    variants = "-"
                # add result
                result.append(
                    {
                        "sample_id": sample.run_metadata.run.sample_name,
                        "parameter": f"{info['abbrev'].upper()} NGS",
                        "result": call,
                        "variants": variants,
                    }
                )
    # annotate species prediction res
    if isinstance(sample.qc_status.status, SampleQcClassification):
        qc_status = sample.qc_status.status.value
    else:
        qc_status = sample.qc_status.status
    # get mykrobe spp results
    try:
        spp_res = next(
            (
                midx.result
                for midx in sample.species_prediction
                if midx.software == "mykrobe"
            )
        )
    except StopIteration:
        spp_res = None
    result.extend(
        [
            {
                "sample_id": sample.run_metadata.run.sample_name,
                "parameter": "MTBC_QC",
                "result": qc_status.capitalize(),
                "variants": "-",
            },
            {
                "sample_id": sample.run_metadata.run.sample_name,
                "parameter": "MTBC_ART",
                "result": spp_res[0].scientific_name if spp_res is not None else "-",
                "variants": "-",
            },
        ]
    )
    # annotate lineage
    for type_res in sample.typing_result:
        if (
            type_res.type == TypingMethod.LINEAGE
            and type_res.software == PredictionSoftware.TBPROFILER
        ):
            # get lineage with longest lineage string
            result.append(
                {
                    "sample_id": sample.run_metadata.run.sample_name,
                    "parameter": "MTBC_LINEAGE",
                    "result": type_res.result.sublineage,
                    "variants": "-",
                }
            )
    df = pd.DataFrame(result)
    if has_failed:
        df["result"] = TBResponses.sample_failed.value
        df["variants"] = "-"
    return df


def sample_to_kmlims(sample: SampleInDatabase) -> pd.DataFrame:
    """Convert sample information to KMLIMS format."""
    match sample.run_metadata.run.analysis_profile:
        case "mycobacterium_tuberculosis":
            pred_res = _fmt_mtuberculosis(sample)
        case _:
            raise NotImplementedError(
                f"No export function for {sample.run_metadata.run.analysis_profile}"
            )
    return pred_res
