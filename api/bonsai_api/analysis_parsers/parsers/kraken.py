"""Parse kraken results."""

import pandas as pd

from prp.models.species import SppMethodIndex, SppPredictionSoftware


def parse_result(file: str, cutoff: float = 0.0001) -> SppMethodIndex:
    """Parse species prediction result"""
    tax_lvl_dict = {
        "P": "phylum",
        "C": "class",
        "O": "order",
        "F": "family",
        "G": "genus",
        "S": "species",
    }
    columns = {"name": "scientific_name"}
    species_pred: pd.DataFrame = (
        pd.read_csv(file, sep="\t")
        .sort_values("fraction_total_reads", ascending=False)
        .rename(columns=columns)
        .replace({"taxonomy_lvl": tax_lvl_dict})
        .loc[lambda df: df["fraction_total_reads"] >= cutoff]
    )
    # cast as method index
    return SppMethodIndex(
        software=SppPredictionSoftware.BRACKEN,
        result=species_pred.to_dict(orient="records"),
    )
