"""Handlers for api services."""
from email import header
import requests
from requests.structures import CaseInsensitiveDict
from pathlib import Path
from flask import current_app
from pydantic import BaseModel, BaseConfig, Field
from functools import wraps


class TokenObject(BaseModel):
    """Token object"""

    token: str
    type: str


def api_authentication(func):
    """Use authentication token for api."""

    @wraps(func)
    def wrapper(token_obj, *args, **kwargs):
        headers = CaseInsensitiveDict()
        headers["Accept"] = "application/json"
        headers["Authorization"] = f"{token_obj.type.capitalize()} {token_obj.token}"

        return func(headers=headers, *args, **kwargs)

    return wrapper


@api_authentication
def get_current_user(headers):
    """Get current user from token"""
    # conduct query
    url = f'{current_app.config["MIMER_API_URL"]}/users/me'
    resp = requests.get(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


def get_auth_token(username: str, password: str) -> TokenObject:
    """Get authentication token from api"""
    # configure header
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    url = f'{current_app.config["MIMER_API_URL"]}/token'
    resp = requests.post(
        url, data={"username": username, "password": password}, headers=headers
    )
    # controll that request
    resp.raise_for_status()
    json_res = resp.json()
    token_obj = TokenObject(token=json_res["access_token"], type=json_res["token_type"])
    return token_obj


@api_authentication
def get_groups(headers):
    """Get groups from database"""
    # conduct query
    url = f'{current_app.config["MIMER_API_URL"]}/groups'
    resp = requests.get(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_samples_in_group(headers, **kwargs):
    """Get groups from database"""
    # conduct query
    group_id = kwargs.get("group_id")
    url = f'{current_app.config["MIMER_API_URL"]}/groups/{group_id}'
    lookup_samples = kwargs.get("lookup_samples", False)
    resp = requests.get(url, headers=headers, params={"lookup_samples": lookup_samples})

    resp.raise_for_status()
    return resp.json()

@api_authentication
def cgmlst_cluster_samples(headers, **kwargs):
    """Get groups from database"""
    url = f'{current_app.config["MIMER_API_URL"]}/cluster/cgmlst'
    resp = requests.post(url, headers=headers)

    resp.raise_for_status()
    return resp.json()