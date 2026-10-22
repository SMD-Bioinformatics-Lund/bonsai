"""MongoDB 4.4 compatible expressions for compact typing columns."""

from typing import Any


def stx_summary_expression() -> dict[str, Any]:
    """List distinct reported symbols in stored hit order."""
    symbols = {
        "$reduce": {
            "input": {
                "$map": {
                    "input": {
                        "$cond": [
                            {"$isArray": "$stx.hits"},
                            "$stx.hits",
                            ["$stx"],  # Previously imported single-gene results.
                        ]
                    },
                    "as": "hit",
                    "in": {"$ifNull": ["$$hit.gene_symbol", ""]},
                }
            },
            "initialValue": [],
            "in": {
                "$cond": [
                    {
                        "$or": [
                            {"$in": ["$$this", ["", "-"]]},
                            {"$in": ["$$this", "$$value"]},
                        ]
                    },
                    "$$value",
                    {"$concatArrays": ["$$value", ["$$this"]]},
                ]
            },
        }
    }
    return {
        "$reduce": {
            "input": symbols,
            "initialValue": "-",
            "in": {
                "$cond": [
                    {"$eq": ["$$value", "-"]},
                    "$$this",
                    {"$concat": ["$$value", ", ", "$$this"]},
                ]
            },
        }
    }


def oh_summary_expression() -> dict[str, Any]:
    """Join O and H predictions, using '-' for each missing component."""
    parts = []
    for field in ("o_type", "h_type"):
        path = f"${field}.sequence_name"
        parts.append({"$cond": [{"$eq": [{"$ifNull": [path, ""]}, ""]}, "-", path]})
    return {"$concat": [parts[0], ":", parts[1]]}
