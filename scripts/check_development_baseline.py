#!/usr/bin/env python3
"""Check generic baseline behaviors in isolation, without a live database/API.

Run against an extracted, pinned development tree in a network-disabled test
container. Only generic inventory cells, comments and authorization stubs are
used. No parser or downstream analysis service is executed.
"""

import argparse
import asyncio
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.responses import JSONResponse
from mongomock import MongoClient

from bonsai_api.crud.metadata import add_metadata_to_sample
from bonsai_api.crud.sample import add_comment
from bonsai_api.io import parse_metadata_table
from bonsai_api.models.metadata import GenericMetadataEntry, InputTableMetadata
from bonsai_api.models.sample import Comment


class Collection:
    def __init__(self, readers):
        self.store = MongoClient().test.sample
        self.store.insert_one({"sample_id": "record", "metadata": [], "comments": []})
        self.reads = 0
        self.readers = readers
        self.barrier = asyncio.Event()

    @property
    def record(self):
        return self.store.find_one({"sample_id": "record"})

    async def find_one(self, query, **kwargs):
        snapshot = deepcopy(self.record)
        self.reads += 1
        if self.reads <= self.readers:
            if self.reads == self.readers:
                self.barrier.set()
            await self.barrier.wait()
        return snapshot

    async def update_one(self, query, update):
        return self.store.update_one(query, update)


async def races():
    cases = []
    store = Collection(2)
    db = SimpleNamespace(sample_collection=store)
    values = [GenericMetadataEntry(fieldname=name, category="inventory", type="string", value="generic text") for name in ["one", "two"]]
    replies = await asyncio.gather(*(add_metadata_to_sample("record", [value], db) for value in values))
    retained = len(store.record["metadata"])
    cases.append({"id": "RECOVERY-METADATA-LOSS", "requests": 2, "successful_replies": replies.count(True), "retained_fields": retained,
                  "issue_reproduced": replies.count(True) == 2 and retained == 1,
                  "method": "Real baseline CRUD; deterministic simultaneous empty-record snapshots; in-memory Mongo substitute"})
    store = Collection(5)
    db = SimpleNamespace(sample_collection=store)
    ctx = SimpleNamespace(actor=SimpleNamespace(id="generic-user"))
    await asyncio.gather(*(add_comment(db, "record", Comment(username="generic-user", comment=f"Generic note {n}"), ctx) for n in range(5)))
    comments = store.record["comments"]
    ids = {row["id"] for row in comments}
    cases.append({"id": "RECOVERY-COMMENT-IDENTITIES", "requests": 5, "retained_comments": len(comments), "distinct_ids": len(ids),
                  "issue_reproduced": len(comments) == 5 and len(ids) < 5,
                  "method": "Real baseline CRUD; deterministic simultaneous snapshots; in-memory Mongo substitute"})
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = asyncio.run(races())
    table = parse_metadata_table(InputTableMetadata(fieldname="inventory", value="Item,Count\nDesk,\nChair,2\n"))
    error = None
    try:
        JSONResponse(table.model_dump(mode="json"))
    except ValueError as exc:
        error = str(exc)
    cases.append({"id": "CSV-EMPTY-CELL-500", "issue_reproduced": error is not None,
                  "observed": error, "method": "Real baseline CSV reader and JSON response serializer, with a generic inventory table"})
    result = {"application_source": "21eccf7075fb59a897cb2ae86b0d6cdb95d0089c", "network": "disabled by container invocation",
              "live_api_contacted": False, "live_database_contacted": False, "analysis_or_biological_parser_executed": False, "cases": cases}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(cases))
    if not all(case["issue_reproduced"] for case in cases):
        raise SystemExit("At least one assumed baseline issue was not reproduced")


if __name__ == "__main__":
    main()
