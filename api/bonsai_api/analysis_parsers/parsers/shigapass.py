"""Functions for parsing shigapass result."""

import logging
import re

import numpy as np
import pandas as pd

from ..models.typing import ShigaTypingMethodIndex, TypingMethod, TypingResultShiga
from ..models.typing import TypingSoftware as Software

LOG = logging.getLogger(__name__)


def parse_shiga_pred(path: str) -> ShigaTypingMethodIndex:
    """Parse shigapass prediction results."""
    LOG.info("Parsing shigapass prediction")
    cols = {
        "Name": "sample_name",
        "rfb_hits,(%)": "rfb_hits",
        "MLST": "mlst",
        "fliC": "flic",
        "CRISPR": "crispr",
        "ipaH": "ipah",
        "Predicted_Serotype": "predicted_serotype",
        "Predicted_FlexSerotype": "predicted_flex_serotype",
        "Comments": "comments",
    }
    # read as dataframe and process data structure
    hits = (
        pd.read_csv(path, delimiter=";", na_values=["ND", "none"])
        .rename(columns=cols)
        .replace(np.nan, None)
    )
    shigatype_results = _parse_shigapass_results(hits, 0)
    return ShigaTypingMethodIndex(
        type=TypingMethod.SHIGATYPE,
        result=shigatype_results,
        software=Software.SHIGAPASS,
    )


def _extract_percentage(rfb_hits: str) -> float:
    pattern = r"([0-9\.]+)%"
    match = re.search(pattern, rfb_hits)
    if match:
        percentile_value = float(match.group(1))
    else:
        percentile_value = 0.0
    return percentile_value


def _parse_shigapass_results(predictions: pd.DataFrame, row: int) -> TypingResultShiga:
    return TypingResultShiga(
        rfb=predictions.loc[row, "rfb"],
        rfb_hits=_extract_percentage(str(predictions.loc[row, "rfb_hits"])),
        mlst=predictions.loc[row, "mlst"],
        flic=predictions.loc[row, "flic"],
        crispr=predictions.loc[row, "crispr"],
        ipah=str(predictions.loc[row, "ipah"]),
        predicted_serotype=str(predictions.loc[row, "predicted_serotype"]),
        predicted_flex_serotype=predictions.loc[row, "predicted_flex_serotype"],
        comments=predictions.loc[row, "comments"],
    )
