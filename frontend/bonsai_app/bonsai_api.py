"""Handlers for api services."""

import logging

import requests
from bonsai_libs.api_client.bonsai import BonsaiApiClient
from bonsai_libs.api_client.core import BearerTokenAuth
from flask import current_app, g
from flask_login import current_user

LOG = logging.getLogger(__name__)


def create_api_client(token: str | None = None) -> BonsaiApiClient:
    """Apply frontend transport settings to authenticated and login requests."""
    http_session = requests.Session()
    verify_ssl = current_app.config["VERIFY_SSL"]
    # Requests expects a string for a custom CA bundle, not a pathlib.Path.
    http_session.verify = verify_ssl if isinstance(verify_ssl, bool) else str(verify_ssl)
    return BonsaiApiClient(
        base_url=current_app.config["API_INTERNAL_URL"],
        timeout=current_app.config["REQUEST_TIMEOUT"],
        session=http_session,
        auth=BearerTokenAuth(token) if token is not None else None,
    )


def get_api_client():
    """Get API client instance using token from logged in user."""

    if "api_client" not in g:
        g.api_client = create_api_client(current_user.token)
    return g.api_client


def update_variant_curation(client, *, curation_id, record):
    """Use the SDK transport for the variant curation update endpoint."""
    return client.request_json(
        "PUT",
        f"analysis/curations/{curation_id}",
        json=record.model_dump(
            mode="json", include={"decision", "rejection_reason", "phenotypes"}
        ),
    ).data
