"""Parse spaTyper results."""

import logging

import pandas as pd

from ..models.sample import SpatyperTypingMethodIndex
from ..models.typing import TypingMethod, TypingResultSpatyper
from ..models.typing import TypingSoftware as Software

LOG = logging.getLogger(__name__)


def parse_spatyper_results(path: str) -> SpatyperTypingMethodIndex:
    """Read spaTyper output file."""
    LOG.info("Parsing spatyper results")

    result_loa = (
        pd.read_csv(path, delimiter="\t")
        .rename(
            columns={
                "Sequence name": "sequence_name",
                "Repeats": "repeats",
                "Type": "type",
            }
        )
        .to_dict(orient="records")
    )

    result = result_loa[0] if result_loa else {}

    result_obj = TypingResultSpatyper(
        sequence_name=str(sequence_name) if (sequence_name := result.get("sequence_name")) else None,
        repeats=str(repeats) if (repeats := result.get("repeats")) else None,
        type=str(type) if (type := result.get("type")) else None,
    )

    return SpatyperTypingMethodIndex(
        type=TypingMethod.SPATYPE, software=Software.SPATYPER, result=result_obj
    )
