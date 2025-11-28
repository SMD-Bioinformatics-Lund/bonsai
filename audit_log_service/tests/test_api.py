"""Test api entrypoints."""

from http import HTTPStatus


def test_root_endpoint(client):
    """Test that root entry point present the service."""
    resp = client.get("/")
    assert resp.status_code == HTTPStatus.OK
    assert "message" in resp.json()
    assert "version" in resp.json()


def test_add_event(client, repo):
    """Test that entrypoint for adding a event accepts the expected data."""
    payload = {
        "source_service": "Test",
        "event_type": "TEST_ACTION",
        "actor": {"type": "system", "id": "test-actor-1"},
        "subject": {"type": "system", "id": "test-subject-1"},
        "severity": "info",
        "metadata": {},
    }
    # TEST that job was accepted
    resp = client.post("/events", json=payload)
    assert resp.status_code == HTTPStatus.ACCEPTED

    # TEST that a DB id was returned
    body = resp.json()
    assert "id" in body and isinstance(body["id"], str) and len(body["id"]) in (24, 12)


def test_add_events(client, repo):
    """Test that entrypoint for adding a event accepts the expected data."""
    n_records_before: int = len(list(repo._col.find()))
    payload = [
        {
            "source_service": "Test",
            "event_type": "TEST_ACTION",
            "actor": {"type": "system", "id": "test-actor-1"},
            "subject": {"type": "system", "id": "test-subject-1"},
            "severity": "info",
            "metadata": {},
        },
        {
            "source_service": "Test 2",
            "event_type": "TEST_ACTION",
            "actor": {"type": "system", "id": "test-actor-2"},
            "subject": {"type": "system", "id": "test-subject-2"},
            "severity": "info",
            "metadata": {},
        },
    ]
    # TEST that job was accepted
    resp = client.post("/events:batch", json=payload)
    assert resp.status_code == HTTPStatus.ACCEPTED

    # TEST that a DB id was returned
    body = resp.json()
    assert "ids" in body and isinstance(body["ids"], list)

    # TEST that each event got a inserted id
    n_ids = len(body.get("ids", []))
    assert n_ids == len(payload)

    # TEST that a record was inserted
    records = list(repo._col.find())
    assert len(records) == n_records_before + len(payload)
