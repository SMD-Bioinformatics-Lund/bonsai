"""Exercise forced save interleavings and replayed generic comment requests."""

import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest
from bonsai_api.crud.metadata import add_metadata_to_sample
from bonsai_api.crud.sample import add_comment
from bonsai_api.exceptions import ConflictError, EntryNotFound
from bonsai_api.models.metadata import GenericMetadataEntry
from bonsai_api.models.sample import Comment
from mongomock import MongoClient


class Collection:
    """Single-document store with simultaneous initial snapshots and atomic updates."""

    def __init__(self, readers=1):
        self.store = MongoClient().test.sample
        self.store.insert_one({"sample_id": "record", "metadata": [], "comments": []})
        self.reads = 0
        self.barrier = asyncio.Event()
        self.readers = readers

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


def db(collection):
    return SimpleNamespace(sample_collection=collection)


def context(actor="alice"):
    return SimpleNamespace(actor=SimpleNamespace(id=actor))


def metadata(name):
    return GenericMetadataEntry(fieldname=name, category="general", type="string", value="text")


@pytest.mark.asyncio
async def test_simultaneous_independent_metadata_is_retained():
    store = Collection(2)
    await asyncio.gather(*(add_metadata_to_sample("record", [metadata(name)], db(store)) for name in ["one", "two"]))
    assert {row["fieldname"] for row in store.record["metadata"]} == {"one", "two"}


@pytest.mark.asyncio
async def test_simultaneous_duplicate_field_has_one_winner():
    store = Collection(3)
    results = await asyncio.gather(*(add_metadata_to_sample("record", [metadata("one")], db(store)) for _ in range(3)), return_exceptions=True)
    assert results.count(True) == 1
    assert sum(isinstance(result, FileExistsError) for result in results) == 2
    assert len(store.record["metadata"]) == 1


@pytest.mark.asyncio
async def test_duplicate_field_inside_one_batch_is_rejected():
    store = Collection()
    with pytest.raises(FileExistsError):
        await add_metadata_to_sample("record", [metadata("one"), metadata("one")], db(store))
    assert store.record["metadata"] == []


@pytest.mark.asyncio
async def test_simultaneous_comments_have_distinct_ids():
    store = Collection(5)
    await asyncio.gather(*(add_comment(db(store), "record", Comment(username="alice", comment=str(i)), context()) for i in range(5)))
    assert len(store.record["comments"]) == 5
    assert len({row["id"] for row in store.record["comments"]}) == 5


@pytest.mark.asyncio
async def test_concurrent_replay_creates_one_comment_and_hides_internal_key():
    store = Collection(3)
    async def send():
        return await add_comment(db(store), "record", Comment(username="alice", comment="one"), context(), request_key="retry-1")
    responses = await asyncio.gather(*(send() for _ in range(3)))
    assert len(store.record["comments"]) == 1
    assert all(len(response) == 1 for response in responses)
    assert all("_request_key" not in row.model_dump() for response in responses for row in response)


@pytest.mark.asyncio
async def test_replay_with_changed_content_conflicts():
    store = Collection()
    await add_comment(db(store), "record", Comment(username="alice", comment="one"), context(), request_key="retry-1")
    with pytest.raises(ConflictError):
        await add_comment(db(store), "record", Comment(username="alice", comment="two"), context(), request_key="retry-1")
    assert len(store.record["comments"]) == 1


@pytest.mark.asyncio
async def test_request_keys_are_scoped_to_authenticated_actor():
    store = Collection()
    for actor in ["alice", "bob"]:
        await add_comment(db(store), "record", Comment(username=actor, comment="one"), context(actor), request_key="retry-1")
    assert len(store.record["comments"]) == 2


@pytest.mark.asyncio
async def test_missing_comment_target_has_a_normal_not_found_error():
    store = Collection()
    async def missing(*args, **kwargs):
        return None
    store.find_one = missing
    with pytest.raises(EntryNotFound):
        await add_comment(db(store), "missing", Comment(username="alice", comment="one"), context())
