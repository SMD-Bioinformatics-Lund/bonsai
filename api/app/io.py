"""File IO operations."""
import logging
import mimetypes
import os
import pathlib
import re
from collections import defaultdict
from typing import List
import pandas as pd
from prp.models.phenotype import GeneBase, PredictionSoftware, VariantBase
from pydantic import BaseModel

from .models.sample import SampleInDatabase

from fastapi.responses import Response

LOG = logging.getLogger(__name__)
BYTE_RANGE_RE = re.compile(r"bytes=(\d+)-(\d+)?$")

TARGETED_ANTIBIOTICS = {
    "rifampicin": "rif",
    "isoniazid": "inh",
    "pyrazinamide": "pza",
    "ethambutol": "etm",
    "amikacin": "ami",
    "levofloxacin": "lev",
}

class InvalidRangeError(Exception):
    pass


class RangeOutOfBoundsError(Exception):
    pass


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
        return False

    if not os.access(path, os.R_OK):
        LOG.warning("file: %s cant read by the system user", file_path)
        return False

    return True


def parse_byte_range(byte_range):
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


def send_partial_file(path, range_header):
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
    result = defaultdict(list)
    for motif in prediction:
        if len(motif.phenotypes) == 0:
            result["none"].append(motif)
        else:
            # add variant to all phenotypes
            for phenotype in motif.phenotypes:
                # make a copy with only one phenotypes
                upd_motif = motif.model_copy(update={"phenotypes": [phenotype]})
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
    variant_desc = f"{variant.reference_sequence}_{variant.start}_{var_type}"
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
    result = []
    for pred_res in sample.element_type_result:
        # only include TBprofiler result
        if not pred_res.software == PredictionSoftware.TBPROFILER:
            continue

        # reformat predicted resistance
        sorted_variants = _sort_motifs_on_phenotype(pred_res.result.variants)

        # create tabular result
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
