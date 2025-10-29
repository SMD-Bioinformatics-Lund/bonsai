"""Parse sccmec results."""

import pandas as pd
import logging

from ..models.sample import SccmecTypingMethodIndex
from ..models.typing import (TypingMethod, TypingResultSccmec)
from ..models.typing import TypingSoftware as Software

LOG = logging.getLogger(__name__)


def parse_sccmec_results(path: str) -> SccmecTypingMethodIndex:
    """Read sccmec output file."""
    LOG.info("Parsing sccmec results")

    result_loa = (
        pd.read_csv(path, delimiter="\t")
        .apply(lambda col: col.map(lambda x: None if pd.isna(x) or x == "-" else x))
        .to_dict(orient="records") 
    )

    result = result_loa[0]

    result_obj = TypingResultSccmec(
        type=result.get("type"),
        subtype=result.get("subtype"),
        mecA=result.get("mecA"),
        targets=list(map(str, targets.split(","))) if (targets := result.get("targets")) else None,
        regions=list(map(str, regions.split(","))) if (regions := result.get("regions")) else None,
        target_schema=result.get("target_schema"),
        target_schema_version=result.get("target_schema_version"),
        region_schema=result.get("region_schema"),
        region_schema_version=result.get("region_schema_version"),
        camlhmp_version=result.get("camlhmp_version"),
        coverage=list(map(float, str(coverage).split(","))) if (coverage := result.get("coverage")) else None,
        hits=list(map(int, str(hits).split(","))) if (hits := result.get("hits")) else None,
        target_comment=result.get("target_comment"),
        region_comment=result.get("region_comment"),
        comment=result.get("comment"),
    )

    return SccmecTypingMethodIndex(
        type=TypingMethod.SCCMECTYPE,
        software=Software.SCCMEC,
        result=result_obj
    )
