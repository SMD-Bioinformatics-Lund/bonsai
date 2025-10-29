"""Functions for parsing emmtyper result."""

import logging
from typing import Any, Iterable

import pandas as pd

from ..models.typing import EmmTypingMethodIndex, TypingMethod, TypingResultEmm
from ..models.typing import TypingSoftware as Software

LOG = logging.getLogger(__name__)


def parse_emm_pred(path: str) -> Iterable[EmmTypingMethodIndex]:
    """Parse emmtyper's output re emm-typing"""
    LOG.info("Parsing emmtyper results")
    pred_result = []
    df = pd.read_csv(path, sep="\t", header=None)
    df.columns = [
        "sample_name",
        "cluster_count",
        "emmtype",
        "emm_like_alleles",
        "emm_cluster",
    ]
    df.replace(["-", ""], None, inplace=True)
    df_loa = df.to_dict(orient="records")
    for emmtype_array in df_loa:
        emmtype_results = _parse_emmtyper_results(emmtype_array)
        pred_result.append(
            EmmTypingMethodIndex(
                type=TypingMethod.EMMTYPE,
                result=emmtype_results,
                software=Software.EMMTYPER,
            )
        )
    return pred_result


def _parse_emmtyper_results(info: dict[str, Any]) -> TypingResultEmm:
    """Parse emm gene prediction results."""
    emm_like_alleles = (
        info["emm_like_alleles"].split(";")
        if not pd.isna(info["emm_like_alleles"])
        else None
    )
    return TypingResultEmm(
        cluster_count=int(info["cluster_count"]),
        emmtype=info["emmtype"],
        emm_like_alleles=emm_like_alleles,
        emm_cluster=info["emm_cluster"],
    )
