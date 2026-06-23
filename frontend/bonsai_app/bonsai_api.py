"""Handlers for api services."""

import logging

from bonsai_libs.api_client.bonsai import BonsaiApiClient
from bonsai_libs.api_client.core import BearerTokenAuth
from flask import current_app, g
from flask_login import current_user

LOG = logging.getLogger(__name__)


def get_api_client():
    """Get API client instance using token from logged in user."""

    if "api_client" not in g:
        g.api_client = BonsaiApiClient(
            base_url=current_app.config["API_INTERNAL_URL"],
            auth=BearerTokenAuth(current_user.token),
        )
    return g.api_client
