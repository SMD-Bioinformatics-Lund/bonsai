"""Handlers for api services."""
from email import header
import requests
from requests.structures import CaseInsensitiveDict
from pathlib import Path
from flask import current_app
from pydantic import BaseModel, BaseConfig, Field


class TokenObject(BaseModel):
    """Token object"""
    token: str
    type: str


def get_current_user(token_obj: TokenObject):
    """Get current user from token"""
    # configure header
    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/json"
    headers["Authorization"] = f"{token_obj.type.capitalize()} {token_obj.token}"

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
    resp = requests.post(url, data={"username": username, "password": password}, headers=headers)
    # controll that request 
    resp.raise_for_status()
    json_res = resp.json()
    token_obj = TokenObject(token=json_res['access_token'], type=json_res['token_type'])
    return token_obj