"""MongoDB 4.4 compatible expressions for compact typing columns."""

from typing import Any


def stx_summary_expression() -> dict[str, Any]:
    """List distinct reported symbols without dropping any supporting hits."""
    # Insert each symbol in order; $sortArray requires MongoDB 5.2 or later.
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
                    {
                        "$concatArrays": [
                            {
                                "$filter": {
                                    "input": "$$value",
                                    "as": "symbol",
                                    "cond": {"$lt": ["$$symbol", "$$this"]},
                                }
                            },
                            ["$$this"],
                            {
                                "$filter": {
                                    "input": "$$value",
                                    "as": "symbol",
                                    "cond": {"$gt": ["$$symbol", "$$this"]},
                                }
                            },
                        ]
                    },
                ]
            },
        }
    }
    joined = {
        "$reduce": {
            "input": symbols,
            "initialValue": "",
            "in": {
                "$concat": [
                    "$$value",
                    {"$cond": [{"$eq": ["$$value", ""]}, "", ", "]},
                    "$$this",
                ]
            },
        }
    }
    return {
        "$let": {
            "vars": {"text": joined},
            "in": {"$cond": [{"$eq": ["$$text", ""]}, "-", "$$text"]},
        }
    }


def oh_summary_expression() -> dict[str, Any]:
    """Combine the O and H predictions, preserving partially typed samples."""
    return {
        "$let": {
            "vars": {
                "o": {"$ifNull": ["$o_type.sequence_name", ""]},
                "h": {"$ifNull": ["$h_type.sequence_name", ""]},
            },
            "in": {
                "$cond": [
                    {
                        "$and": [
                            {"$in": ["$$o", ["", "-"]]},
                            {"$in": ["$$h", ["", "-"]]},
                        ]
                    },
                    "-",
                    {
                        "$concat": [
                            {"$cond": [{"$eq": ["$$o", ""]}, "-", "$$o"]},
                            ":",
                            {"$cond": [{"$eq": ["$$h", ""]}, "-", "$$h"]},
                        ]
                    },
                ]
            },
        }
    }
