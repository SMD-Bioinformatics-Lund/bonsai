"""Handlers for api services."""

import logging

import requests
from bonsai_libs.api_client.bonsai import BonsaiApiClient
from bonsai_libs.api_client.core import BearerTokenAuth
from flask import current_app, g
from flask_login import current_user

LOG = logging.getLogger(__name__)


def get_api_client():
    if "api_client" not in g:
        # get token from current user
        token = current_user.token.access_token

        g.api_client = BonsaiApiClient(
            base_url=current_app.config["API_INTERNAL_URL"],
            auth=BearerTokenAuth(token),
        )
    return g.api_client


def fetch_user_data(base_url: str, token: str) -> dict | None:
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(
        f"{base_url}/users/me",
        headers=headers,
        timeout=5,
    )

    if resp.status_code != 200:
        return None

    return resp.json()


def authenticate_user(base_url: str, username: str, password: str) -> dict[str, str]:

    resp = requests.post(
        f"{base_url}/token",
        data={"username": username, "password": password},
        timeout=5,
    )

    if resp.status_code != 200:
        raise ValueError("Login failed: {resp.status_code}")
    return resp.json()
