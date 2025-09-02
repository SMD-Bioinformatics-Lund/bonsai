"""Test api entrypoints."""

from fastapi.testclient import TestClient

from notification_service.main import create_api_app

client = TestClient(create_api_app())


def test_root_endpoint():
    """Test that root entry point present the service."""

    app = create_api_app()
    with TestClient(app) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "message" in resp.json()
        assert "version" in resp.json()


def test_send_email_missing_message():
    """Test that entrypoint for sending accepts expected input."""
    payload = {
        "recipient": ["test@example.com"],
        "subject": "Test",
        "content_type": "plain",
    }
    app = create_api_app()
    with TestClient(app) as client:
        resp = client.post("/send-email", json=payload)
        assert resp.status_code == 422 or resp.status_code == 400
