"""Typing-summary regressions against a disposable MongoDB database.

Set BONSAI_TEST_MONGODB_URI and run with unittest discovery from api/:
    python -m unittest discover -s tests/crud -p test_typing_summary.py -v
Each run creates and removes its own uniquely named database.
"""

import os
import unittest
from uuid import uuid4

from pymongo import MongoClient

from bonsai_api.crud.builder.summary import compile_summary_pipeline
from bonsai_api.crud.builder.summary_manifest import MANIFEST
from bonsai_libs.parse.models.typing import TypingResultStx


def entry(analysis_type, result, software=None):
    software = software or (
        "virulencefinder" if analysis_type == "stx" else "serotypefinder"
    )
    if software == "virulencefinder" and analysis_type == "stx":
        if isinstance(result, dict) and result.get("hits"):
            payload = {
                **result,
                "hits": [
                    {"element_type": "VIRULENCE", "element_subtype": "VIRULENCE", **hit}
                    for hit in result["hits"]
                ],
            }
            result = TypingResultStx.model_validate(payload).model_dump(
                exclude_none=True
            )
    return {
        "software": software,
        "analysis_type": analysis_type,
        "status": "parsed" if result else "absent",
        "result": result,
        "summary": {},
    }


def case(name, typing_result=None, expected=None, fields=None):
    document = {"sample_id": "sample-1"}
    if typing_result is not None:
        document["typing_result"] = typing_result
    return {
        "name": name,
        "document": document,
        "fields": fields or ["sample_id", "stx", "oh"],
        "expected": {
            "sample_id": "sample-1",
            **(expected or {"stx": "-", "oh": "-:-"}),
        },
    }


MULTI_HIT = entry(
    "stx",
    {
        "hits": [
            {"gene_symbol": "stx2a", "accession": "ref-2", "ref_database": "stx"},
            {"gene_symbol": "stx1a", "accession": "ref-1", "ref_database": "stx"},
            {
                "gene_symbol": "stx2a",
                "accession": "ref-3",
                "ref_database": "virulence_ecoli",
            },
            {"gene_symbol": "stx2c-O157-FLY16", "ref_database": "virulence_ecoli"},
        ]
    },
)
TYPING_ENTRIES = [
    entry("h_type", {"sequence_name": "H7"}),  # H first must not override O.
    entry("o_type", {"sequence_name": "wrong-O"}, software="other-software"),
    entry("o_type", {"sequence_name": "O157"}),
    entry("other_analysis", {"gene_symbol": "wrong-STX"}, software="virulencefinder"),
    entry("stx", {"gene_symbol": "wrong-STX"}, software="other-software"),
    MULTI_HIT,
    entry("mlst", {"sequence_type": 11}, software="mlst"),
]
CASES = [
    case(
        "older multi-hit result without display field",
        [
            {
                "software": "virulencefinder",
                "analysis_type": "stx",
                "result": {"hits": [{"gene_symbol": "stx2a"}]},
            }
        ],
    ),
    case("missing typing"),
    case("empty typing", []),
    case(
        "absent results",
        [entry("stx", None), entry("o_type", None), entry("h_type", None)],
    ),
    case("empty hits", [entry("stx", {"hits": []})]),
    case(
        "empty symbols",
        [entry("stx", {"hits": [{}, {"gene_symbol": None}, {"gene_symbol": ""}]})],
    ),
    case(
        "legacy single hit",
        [entry("stx", {"gene_symbol": "stx2a"})],
        {"stx": "stx2a", "oh": "-:-"},
    ),
    case(
        "single object source",
        entry("stx", {"gene_symbol": "stx1a"}),
        {"stx": "stx1a", "oh": "-:-"},
    ),
    case(
        "multiple types preserve order and deduplicate subtypes across databases",
        [MULTI_HIT],
        {"stx": "stx2, stx1", "oh": "-:-"},
    ),
    case(
        "O only",
        [entry("o_type", {"sequence_name": "O157"})],
        {"stx": "-", "oh": "O157:-"},
    ),
    case(
        "H only", [entry("h_type", {"sequence_name": "H7"})], {"stx": "-", "oh": "-:H7"}
    ),
    case(
        "blank O",
        [
            entry("o_type", {"sequence_name": ""}),
            entry("h_type", {"sequence_name": "H7"}),
        ],
        {"stx": "-", "oh": "-:H7"},
    ),
    case(
        "both placeholders",
        [
            entry("o_type", {"sequence_name": "-"}),
            entry("h_type", {"sequence_name": "-"}),
        ],
    ),
    case(
        "combined summaries",
        TYPING_ENTRIES,
        {
            "stx": "stx2, stx1",
            "oh": "O157:H7",
            "mlst_sequence_type": 11,
        },
        ["sample_id", "stx", "oh", "mlst_sequence_type"],
    ),
    case(
        "STX subset",
        TYPING_ENTRIES,
        {"stx": "stx2, stx1"},
        ["sample_id", "stx"],
    ),
    case("OH subset", TYPING_ENTRIES, {"oh": "O157:H7"}, ["sample_id", "oh"]),
]


@unittest.skipUnless(
    os.getenv("BONSAI_TEST_MONGODB_URI"),
    "Set BONSAI_TEST_MONGODB_URI for MongoDB checks",
)
class TypingSummaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = MongoClient(
            os.environ["BONSAI_TEST_MONGODB_URI"], serverSelectionTimeoutMS=5000
        )
        cls.db = cls.client[f"bonsai_typing_summary_test_{uuid4().hex}"]

    @classmethod
    def tearDownClass(cls):
        cls.client.drop_database(cls.db.name)
        cls.client.close()

    def test_summary_values_and_unchanged_evidence(self):
        collection = self.db.samples
        for scenario in CASES:
            with self.subTest(scenario["name"]):
                collection.delete_many({})
                collection.insert_one(dict(scenario["document"]))
                original = collection.find_one()
                pipeline = compile_summary_pipeline(None, MANIFEST, scenario["fields"])
                self.assertEqual(
                    list(collection.aggregate(pipeline)), [scenario["expected"]]
                )
                self.assertEqual(collection.find_one(), original)
